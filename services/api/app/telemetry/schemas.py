"""Pydantic envelope for telemetry batches. Reused in later storage work."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID
    timestamp: datetime
    sessionId: str = Field(min_length=1)
    userId: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    schemaVersion: str = Field(min_length=1)
    requestId: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent]


class TelemetryReceivedResponse(BaseModel):
    received: int


class TelemetryStoreResponse(BaseModel):
    received: int
    stored: int
    rejected: int


class TelemetryPeriod(BaseModel):
    from_ts: str
    to_ts: str

    model_config = ConfigDict(populate_by_name=True)

    def model_dump_period(self) -> dict[str, str]:
        return {"from": self.from_ts, "to": self.to_ts}


class TelemetryReportResponse(BaseModel):
    period: dict[str, str]
    metrics: dict[str, list[dict[str, Any]]]


class TelemetryBatchRaw(BaseModel):
    """Loose envelope: items are raw dicts so one invalid event cannot 422 the batch."""

    model_config = ConfigDict(extra="forbid")

    events: list[Any]
