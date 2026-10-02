"""Telemetry ingest and operational report."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import ValidationError

from app.cache import TELEMETRY_REPORT_TTL_SECONDS, report_cache
from app.telemetry.analysis import build_metrics
from app.telemetry.schemas import (
    TelemetryBatchRaw,
    TelemetryEvent,
    TelemetryReportResponse,
    TelemetryStoreResponse,
)
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


@router.get("/report", response_model=TelemetryReportResponse)
def telemetry_report(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
) -> TelemetryReportResponse:
    now = datetime.now(timezone.utc)
    end = end_date.astimezone(timezone.utc) if end_date else now
    start = start_date.astimezone(timezone.utc) if start_date else end - timedelta(days=7)
    cache_key = f"v1:telemetry:report:{start.isoformat()}:{end.isoformat()}"
    cached = report_cache.get(cache_key)
    if cached is not None:
        return TelemetryReportResponse.model_validate(cached)
    payload = TelemetryReportResponse(
        period={"from": start.isoformat(), "to": end.isoformat()},
        metrics=build_metrics(start, end),
    )
    report_cache.set(cache_key, payload.model_dump(), ttl=TELEMETRY_REPORT_TTL_SECONDS)
    return payload
