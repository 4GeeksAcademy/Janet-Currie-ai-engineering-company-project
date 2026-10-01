"""Map TelemetryEvent rows and bulk-insert into Supabase PostgREST."""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

import httpx

from app.telemetry.schemas import TelemetryEvent

logger = logging.getLogger(__name__)

ERROR_TYPES = {"frontend_error_raised"}
WARN_TYPES = {
    "user_login_failed",
    "session_expired",
    "outbound_order_rejected",
    "direct_stock_edit_rejected",
    "inbound_order_validation_failed",
}


class EventInserter(Protocol):
    def __call__(self, rows: list[dict[str, Any]]) -> int: ...


def level_for(event_type: str) -> str:
    if event_type in ERROR_TYPES:
        return "error"
    if event_type in WARN_TYPES:
        return "warn"
    return "info"


def _numeric(properties: dict[str, Any]) -> float | None:
    for key in ("duration_ms", "quantity", "value"):
        raw = properties.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            return float(raw)
    return None


def event_to_row(event: TelemetryEvent) -> dict[str, Any]:
    props = dict(event.properties)
    tags: dict[str, Any] = {
        **props,
        "eventId": str(event.eventId),
        "sessionId": event.sessionId,
        "userId": event.userId,
        "schemaVersion": event.schemaVersion,
        "requestId": event.requestId,
    }
    return {
        "timestamp": event.timestamp.isoformat(),
        "service": "backoffice",
        "event_type": event.event_type,
        "level": level_for(event.event_type),
        "value": _numeric(props),
        "message": None,
        "tags": tags,
    }


def supabase_insert(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        logger.warning("supabase telemetry insert skipped: missing SUPABASE_URL or key")
        return 0
    endpoint = f"{url}/rest/v1/telemetry_events"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    response = httpx.post(endpoint, headers=headers, json=rows, timeout=20.0)
    response.raise_for_status()
    return len(rows)


_inserter: EventInserter = supabase_insert


def set_inserter(fn: EventInserter | None) -> None:
    global _inserter
    _inserter = fn or supabase_insert


def bulk_insert(rows: list[dict[str, Any]]) -> int:
    return _inserter(rows)
