"""Per-event validation and bulk insert without cancelling mixed batches."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.telemetry import store
from tests.helpers import client


@pytest.fixture(autouse=True)
def _memory_insert() -> None:
    bucket: list[dict] = []

    def insert(rows: list[dict]) -> int:
        bucket.extend(rows)
        return len(rows)

    store.set_inserter(insert)
    yield bucket
    store.set_inserter(None)


def _event(event_type: str = "page_viewed", **overrides: object) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "eventId": str(uuid4()),
        "timestamp": now,
        "sessionId": "session-test",
        "userId": "42",
        "event_type": event_type,
        "schemaVersion": "1.0.0",
        "requestId": str(uuid4()),
        "properties": {"route": "/operations"},
    }
    payload.update(overrides)
    return payload


def test_mixed_batch_stores_valid_and_counts_rejected(_memory_insert: list[dict]) -> None:
    response = client.post(
        "/telemetry/events",
        json={"events": [_event("page_viewed"), {"event_type": "broken"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"received": 2, "stored": 1, "rejected": 1}
    assert _memory_insert[0]["event_type"] == "page_viewed"
    assert _memory_insert[0]["service"] == "backoffice"
    assert "eventId" in _memory_insert[0]["tags"]


def test_all_valid_batch(_memory_insert: list[dict]) -> None:
    response = client.post(
        "/telemetry/events",
        json={"events": [_event("inbound_order_created"), _event("page_viewed")]},
    )
    assert response.json() == {"received": 2, "stored": 2, "rejected": 0}
    assert len(_memory_insert) == 2


def test_empty_batch() -> None:
    response = client.post("/telemetry/events", json={"events": []})
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}


def test_missing_events_key_is_422() -> None:
    assert client.post("/telemetry/events", json={}).status_code == 422
