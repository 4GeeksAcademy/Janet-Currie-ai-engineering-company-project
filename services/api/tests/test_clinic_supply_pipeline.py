"""Clinic supply transform, quarantine, idempotency, and optional heartbeat."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pipelines import pipeline as clinic_pipeline


def _event(
    event_type: str,
    *,
    event_id: str,
    clinic_id: int = 1,
    country: str = "US",
    timestamp: str = "2026-07-15T12:00:00+00:00",
    quantity: int | None = 2,
    unit_cost: float | None = None,
) -> dict:
    tags: dict = {
        "eventId": event_id,
        "clinic_id": clinic_id,
        "country": country,
    }
    if quantity is not None:
        tags["quantity"] = quantity
    if unit_cost is not None:
        tags["unit_cost"] = unit_cost
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "tags": tags,
    }


def test_empty_events_complete_with_zero_rows() -> None:
    result = clinic_pipeline.transform_clinic_month_kpis([])
    assert result["events_extracted"] == 0
    assert result["events_quarantined"] == 0
    assert result["rows"] == []


def test_four_kpis_hand_calculated_cost_and_counts_not_quantity_sum() -> None:
    events = [
        _event("inbound_order_created", event_id="a", quantity=2, unit_cost=4.5),
        _event("inbound_order_created", event_id="b", quantity=1, unit_cost=10),
        _event("outbound_order_created", event_id="c", quantity=50),
        _event("outbound_order_created", event_id="d", quantity=7),
        _event("stock_threshold_triggered", event_id="e", quantity=3),
        _event("supply_expiry_flagged", event_id="f", quantity=1),
        _event("supply_expiry_flagged", event_id="g", quantity=1),
        _event("supply_expiry_flagged", event_id="h", quantity=1),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    assert result["events_quarantined"] == 0
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["clinic_id"] == "1"
    assert row["currency"] == "USD"
    assert row["month_start"] == "2026-07-01"
    assert row["total_supply_cost"] == pytest.approx(19.0)
    assert row["supply_consumption_count"] == 2
    assert row["critical_stockout_count"] == 1
    assert row["expiry_risk_count"] == 3


def test_duplicate_event_id_counts_once() -> None:
    events = [
        _event("outbound_order_created", event_id="dup", quantity=1),
        _event("outbound_order_created", event_id="dup", quantity=1),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    assert result["rows"][0]["supply_consumption_count"] == 1


def test_bad_cost_clinic_and_country_are_quarantined() -> None:
    events = [
        _event("inbound_order_created", event_id="ok", quantity=1, unit_cost=3),
        _event("inbound_order_created", event_id="cost", quantity=1, unit_cost=0),
        _event("outbound_order_created", event_id="clinic", clinic_id=99),
        _event("outbound_order_created", event_id="country", country="FR"),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    assert result["events_quarantined"] == 3
    assert result["rows"][0]["total_supply_cost"] == pytest.approx(3.0)
    assert result["rows"][0]["supply_consumption_count"] == 0


def test_late_event_uses_utc_month_of_timestamp() -> None:
    events = [
        _event(
            "outbound_order_created",
            event_id="late",
            timestamp="2026-07-31T23:30:00+00:00",
        ),
        _event(
            "outbound_order_created",
            event_id="next",
            timestamp="2026-08-01T00:30:00+00:00",
        ),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    months = {row["month_start"]: row["supply_consumption_count"] for row in result["rows"]}
    assert months["2026-07-01"] == 1
    assert months["2026-08-01"] == 1


def test_us_and_uk_stay_separate_currencies() -> None:
    events = [
        _event("inbound_order_created", event_id="us", clinic_id=1, country="US", unit_cost=2, quantity=1),
        _event("inbound_order_created", event_id="uk", clinic_id=2, country="UK", unit_cost=5, quantity=1),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    by_clinic = {row["clinic_id"]: row for row in result["rows"]}
    assert by_clinic["1"]["currency"] == "USD"
    assert by_clinic["2"]["currency"] == "GBP"
    assert by_clinic["1"]["total_supply_cost"] + by_clinic["2"]["total_supply_cost"] == pytest.approx(7.0)


class _MemoryWarehouse:
    def __init__(self) -> None:
        self.kpis: dict[tuple[str, str], dict] = {}
        self.runs: list[dict] = []

    def extract(self, _start: datetime, _end: datetime) -> list[dict]:
        return [
            _event("inbound_order_created", event_id="a", quantity=2, unit_cost=5),
            _event("outbound_order_created", event_id="b"),
        ]

    def load(self, rows: list[dict]) -> int:
        for row in rows:
            self.kpis[(row["clinic_id"], row["month_start"])] = dict(row)
        return len(rows)

    def insert_run(self, row: dict) -> None:
        self.runs.append(dict(row))

    def update_run(self, run_id: str, fields: dict) -> None:
        for item in self.runs:
            if item["run_id"] == run_id:
                item.update(fields)
                return
        self.runs.append(dict(fields))


@pytest.fixture
def warehouse() -> _MemoryWarehouse:
    store = _MemoryWarehouse()
    clinic_pipeline.set_extract(store.extract)
    clinic_pipeline.set_load(store.load)
    clinic_pipeline.set_run_log(store.insert_run, store.update_run)
    clinic_pipeline.set_readers(
        lambda month: [
            row
            for row in store.kpis.values()
            if month is None or row["month_start"] == month
        ],
        lambda: store.runs[-1] if store.runs else None,
    )
    clinic_pipeline.set_heartbeat(lambda _run_id: None)
    yield store
    clinic_pipeline.reset_pipeline_hooks()


def test_idempotent_rerun_same_window(warehouse: _MemoryWarehouse) -> None:
    first = clinic_pipeline.execute_monthly_clinic_supply_performance(
        datetime(2026, 7, 1, tzinfo=timezone.utc).date()
    )
    snapshot = dict(warehouse.kpis)
    second = clinic_pipeline.execute_monthly_clinic_supply_performance(
        datetime(2026, 7, 1, tzinfo=timezone.utc).date()
    )
    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert warehouse.kpis == snapshot
    assert len(warehouse.kpis) == 1


def test_heartbeat_failure_does_not_fail_flow(warehouse: _MemoryWarehouse) -> None:
    def boom(_run_id: str) -> None:
        raise RuntimeError("heartbeat down")

    clinic_pipeline.set_heartbeat(boom)
    result = clinic_pipeline.execute_monthly_clinic_supply_performance(
        datetime(2026, 7, 1, tzinfo=timezone.utc).date()
    )
    assert result["status"] == "completed"
    assert result["records_processed"] == 1
