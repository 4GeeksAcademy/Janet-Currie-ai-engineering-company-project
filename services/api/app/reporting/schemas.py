"""Pydantic contracts for /reporting routes."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ClinicSupplyKpi(BaseModel):
    clinic_id: str
    country: str
    total_supply_cost: float
    supply_consumption_count: int
    critical_stockout_count: int
    expiry_risk_count: int
    currency: str


class MonthlyClinicSupplyPerformanceResponse(BaseModel):
    month_start: date | None
    clinics: list[ClinicSupplyKpi]


class PipelineRunResponse(BaseModel):
    run_id: str
    status: str
    started_at: str
    finished_at: str | None
    records_processed: int
    events_extracted: int
    events_quarantined: int
    window_start: str
    window_end: str
    error: str | None = None


class PipelineRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month_start: date | None = Field(default=None)
