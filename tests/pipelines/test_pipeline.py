"""Isolated clinic-supply transform tests. No database or HTTP."""

from __future__ import annotations

import inspect

import pytest
from prefect.flows import Flow

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


def test_empty_input_yields_zero_rows() -> None:
    result = clinic_pipeline.transform_clinic_month_kpis([])
    assert result["events_extracted"] == 0
    assert result["events_quarantined"] == 0
    assert result["rows"] == []


def test_four_kpis_hand_calculated_cost_and_consumption_is_count() -> None:
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


def test_malformed_cost_clinic_and_country_are_quarantined() -> None:
    events = [
        _event("inbound_order_created", event_id="ok", quantity=1, unit_cost=3),
        _event("inbound_order_created", event_id="zero", quantity=1, unit_cost=0),
        _event("inbound_order_created", event_id="missing"),
        _event("outbound_order_created", event_id="clinic", clinic_id=99),
        _event("outbound_order_created", event_id="country", country="FR"),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    assert result["events_quarantined"] == 4
    assert len(result["rows"]) == 1
    assert result["rows"][0]["total_supply_cost"] == pytest.approx(3.0)


def test_month_boundary_uses_utc_month_of_timestamp() -> None:
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


def test_us_and_uk_stay_separate_currencies_with_no_combined_total() -> None:
    events = [
        _event("inbound_order_created", event_id="us", clinic_id=1, country="US", unit_cost=2, quantity=1),
        _event("inbound_order_created", event_id="uk", clinic_id=2, country="UK", unit_cost=5, quantity=1),
    ]
    result = clinic_pipeline.transform_clinic_month_kpis(events)
    assert len(result["rows"]) == 2
    by_clinic = {row["clinic_id"]: row for row in result["rows"]}
    assert by_clinic["1"]["currency"] == "USD"
    assert by_clinic["2"]["currency"] == "GBP"
    assert "total" not in result
    assert all("combined" not in row for row in result["rows"])


def test_main_flow_coordinates_named_subflows() -> None:
    coordinator = clinic_pipeline.monthly_clinic_supply_performance
    try:
        source = inspect.getsource(coordinator)
    except TypeError:
        source = inspect.getsource(coordinator.fn)
    assert "extract_clinic_supply_events_flow" in source
    assert "transform_clinic_month_kpis_flow" in source
    assert "load_monthly_clinic_supply_performance_flow" in source
    for name in (
        "extract_clinic_supply_events_flow",
        "transform_clinic_month_kpis_flow",
        "load_monthly_clinic_supply_performance_flow",
        "emit_clinic_supply_pipeline_heartbeat_flow",
        "monthly_clinic_supply_performance",
    ):
        assert isinstance(getattr(clinic_pipeline, name), Flow)
