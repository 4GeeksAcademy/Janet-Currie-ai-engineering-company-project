"""Reporting HTTP contract: auth, empty, 400, 404, 409, populated."""

from __future__ import annotations

from datetime import datetime

import pytest

from pipelines import pipeline as clinic_pipeline
from tests.helpers import auth_header, client


class _Store:
    def __init__(self) -> None:
        self.kpis: list[dict] = []
        self.runs: list[dict] = []

    def extract(self, _start: datetime, _end: datetime) -> list[dict]:
        return [
            {
                "timestamp": "2026-07-10T00:00:00+00:00",
                "event_type": "inbound_order_created",
                "tags": {
                    "eventId": "in-1",
                    "clinic_id": 1,
                    "country": "US",
                    "quantity": 2,
                    "unit_cost": 3,
                },
            }
        ]

    def load(self, rows: list[dict]) -> int:
        self.kpis = [dict(row) for row in rows]
        return len(rows)

    def insert_run(self, row: dict) -> None:
        self.runs.append(dict(row))

    def update_run(self, run_id: str, fields: dict) -> None:
        for item in self.runs:
            if item.get("run_id") == run_id:
                item.update(fields)
                return


@pytest.fixture
def reporting_store() -> _Store:
    store = _Store()
    clinic_pipeline.set_extract(store.extract)
    clinic_pipeline.set_load(store.load)
    clinic_pipeline.set_run_log(store.insert_run, store.update_run)
    clinic_pipeline.set_readers(
        lambda month: [
            row for row in store.kpis if month is None or row["month_start"] == month
        ],
        lambda: store.runs[-1] if store.runs else None,
    )
    clinic_pipeline.set_heartbeat(lambda _rid: None)
    yield store
    clinic_pipeline.reset_pipeline_hooks()


def test_reporting_requires_auth() -> None:
    assert client.get("/reporting/monthly-clinic-supply-performance").status_code == 401
    assert client.get("/reporting/pipeline-runs/latest").status_code == 401
    assert client.post("/reporting/pipeline-runs", json={}).status_code == 401


def test_empty_kpi_get_is_200(reporting_store: _Store) -> None:
    headers = auth_header(email="rep-empty@healthcore.example")
    response = client.get("/reporting/monthly-clinic-supply-performance", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"month_start": None, "clinics": []}


def test_bad_month_start_is_400(reporting_store: _Store) -> None:
    headers = auth_header(email="rep-bad@healthcore.example")
    response = client.get(
        "/reporting/monthly-clinic-supply-performance",
        headers=headers,
        params={"month_start": "2026-07-15"},
    )
    assert response.status_code == 400


def test_latest_run_404_then_post_and_get(reporting_store: _Store) -> None:
    headers = auth_header(email="rep-run@healthcore.example")
    missing = client.get("/reporting/pipeline-runs/latest", headers=headers)
    assert missing.status_code == 404
    created = client.post(
        "/reporting/pipeline-runs",
        headers=headers,
        json={"month_start": "2026-07-01"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "completed"
    assert body["records_processed"] == 1
    latest = client.get("/reporting/pipeline-runs/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["run_id"] == body["run_id"]
    kpis = client.get(
        "/reporting/monthly-clinic-supply-performance",
        headers=headers,
        params={"month_start": "2026-07-01"},
    )
    assert kpis.status_code == 200
    payload = kpis.json()
    assert payload["month_start"] == "2026-07-01"
    assert payload["clinics"][0]["clinic_id"] == "1"
    assert payload["clinics"][0]["total_supply_cost"] == 6
    assert payload["clinics"][0]["currency"] == "USD"


def test_overlapping_post_is_409(reporting_store: _Store) -> None:
    headers = auth_header(email="rep-lock@healthcore.example")
    assert clinic_pipeline.pipeline_lock.acquire(blocking=False)
    try:
        response = client.post(
            "/reporting/pipeline-runs",
            headers=headers,
            json={"month_start": "2026-07-01"},
        )
        assert response.status_code == 409
    finally:
        clinic_pipeline.pipeline_lock.release()
