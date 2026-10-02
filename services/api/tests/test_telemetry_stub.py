"""Stub ingest: format only, no database writes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.routers.telemetry import TELEMETRY_ENDPOINT
from tests.helpers import client


def _event(event_type: str = "page_viewed") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "eventId": str(uuid4()),
        "timestamp": now,
        "sessionId": "session-test",
        "userId": "42",
        "event_type": event_type,
        "schemaVersion": "1.0.0",
        "requestId": str(uuid4()),
        "properties": {"route": "/operations"},
    }


def test_telemetry_endpoint_env_is_configured() -> None:
    assert TELEMETRY_ENDPOINT.endswith("/telemetry/events")


def test_ingest_returns_received_count() -> None:
    payload = {"events": [_event("inbound_order_created"), _event("page_viewed")]}
    response = client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 2}


def test_empty_batch_is_ok() -> None:
    response = client.post("/telemetry/events", json={"events": []})
    assert response.status_code == 200
    assert response.json() == {"received": 0}


def test_invalid_envelope_is_422() -> None:
    response = client.post("/telemetry/events", json={"events": [{"event_type": "x"}]})
    assert response.status_code == 422


def test_unauthenticated_ingest_is_allowed() -> None:
    response = client.post("/telemetry/events", json={"events": [_event()]})
    assert response.status_code == 200
