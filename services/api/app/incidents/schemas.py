"""Explicit output contract for incident analysis JSON."""

from __future__ import annotations

from pydantic import BaseModel


class InvalidBreakdownItem(BaseModel):
    rule: str
    label: str
    count: int


class SatisfactionSummary(BaseModel):
    scored_cases: int
    closed_valid: int
    average_score: float
    histogram: dict[str, int]


class IncidentAnalysisResponse(BaseModel):
    source_file: str
    total_records: int
    valid_count: int
    invalid_count: int
    invalid_breakdown: list[InvalidBreakdownItem]
    category_counts: dict[str, int]
    status_counts: dict[str, int]
    country_counts: dict[str, int]
    satisfaction: SatisfactionSummary
