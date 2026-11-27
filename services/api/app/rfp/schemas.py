"""HTTP contracts for RFP tickets. Raw paths and document text stay off these models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TicketAccepted(BaseModel):
    ticket_id: str
    status: str
    processing_state: str


class TicketSummary(BaseModel):
    ticket_id: str
    status: str
    processing_state: str
    client_name: str | None = None
    client_country: str | None = None
    program_type: str | None = None
    outcome_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketSummary]
    limit: int
    offset: int


class ReadabilityView(BaseModel):
    flesch_reading_ease: float | None = None
    flesch_kincaid_grade: float | None = None
    gunning_fog: float | None = None
    word_count: int | None = None
    sentence_count: int | None = None
    character_count: int | None = None
    page_count: int | None = None
    metric_status: str | None = None


class MetadataView(BaseModel):
    rfp_id: str
    client_name: str | None = None
    client_country: str | None = None
    program_type: str | None = None
    covered_population: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    departments_needed: list[str] = Field(default_factory=list)
    currency: str | None = None
    classification_confidence: float | None = None
    readability: ReadabilityView


class DepartmentView(BaseModel):
    department_id: str
    department_name: str
    owner_name: str
    key_aspects: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class TicketDetail(BaseModel):
    ticket_id: str
    status: str
    processing_state: str
    outcome_reason_code: str | None = None
    message: str
    contains_phi: bool
    requires_compliance_review: bool
    metadata: MetadataView | None = None
    departments: list[DepartmentView] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


SAFE_MESSAGES = {
    "not_an_rfp": "This file is not a request for a HealthCore proposal.",
    "phi_detected": (
        "Protected information was detected. Submit a privacy-safe document so Compliance can handle it."
    ),
    "conversion_failed": "The PDF could not be read. Check the file and try again.",
    "processing_failed": "Intake did not finish. You can retry this ticket.",
    "analyzing": "Intake is still running.",
    "intake_complete": "Intake analysis is ready. This is not a proposal or an approval.",
}


def safe_message(status: str, processing_state: str, reason_code: str | None) -> str:
    if processing_state == "failed":
        return SAFE_MESSAGES["processing_failed"]
    if reason_code in SAFE_MESSAGES:
        return SAFE_MESSAGES[reason_code]
    if status in SAFE_MESSAGES:
        return SAFE_MESSAGES[status]
    return SAFE_MESSAGES["analyzing"]
