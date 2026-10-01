"""Stub telemetry ingest. Validates envelope and acknowledges; no persistence."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter

from app.telemetry.schemas import TelemetryBatch, TelemetryReceivedResponse

logger = logging.getLogger(__name__)

TELEMETRY_ENDPOINT = os.getenv(
    "TELEMETRY_ENDPOINT", "http://localhost:8000/telemetry/events"
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=TelemetryReceivedResponse)
def ingest_events(batch: TelemetryBatch) -> TelemetryReceivedResponse:
    _ = TELEMETRY_ENDPOINT
    types = [event.event_type for event in batch.events]
    logger.info("telemetry_stub received=%s event_types=%s", len(types), types)
    return TelemetryReceivedResponse(received=len(batch.events))
