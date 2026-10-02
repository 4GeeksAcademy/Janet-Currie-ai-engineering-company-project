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
