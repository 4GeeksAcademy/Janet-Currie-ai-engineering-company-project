"""Telemetry ingest: per-event validation and bulk insert. Envelope URL unchanged."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError

from app.telemetry.schemas import TelemetryBatchRaw, TelemetryEvent, TelemetryStoreResponse
from app.telemetry.store import bulk_insert, event_to_row

logger = logging.getLogger(__name__)

TELEMETRY_ENDPOINT = os.getenv(
    "TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events"
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=TelemetryStoreResponse)
def ingest_events(batch: TelemetryBatchRaw) -> TelemetryStoreResponse:
    _ = TELEMETRY_ENDPOINT
    received = len(batch.events)
    valid_rows: list[dict[str, Any]] = []
    rejected = 0
    types: list[str] = []
    for raw in batch.events:
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError:
            rejected += 1
            continue
        types.append(event.event_type)
        valid_rows.append(event_to_row(event))
    stored = bulk_insert(valid_rows) if valid_rows else 0
    logger.info(
        "telemetry_ingest received=%s stored=%s rejected=%s event_types=%s",
        received,
        stored,
        rejected,
        types,
    )
    return TelemetryStoreResponse(received=received, stored=stored, rejected=rejected)
