"""SQLModel tables for RFP intake. Later-part columns stay empty in Part 1."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RfpTicket(SQLModel, table=True):
    __tablename__ = "rfp_ticket"

    ticket_id: str = Field(primary_key=True, max_length=64)
    rfp_id: str | None = Field(default=None, max_length=64, index=True)
    status: str = Field(default="analyzing", max_length=32, index=True)
    processing_state: str = Field(default="queued", max_length=32, index=True)
    raw_pdf_path: str = Field(max_length=255)
    task_id: str | None = Field(default=None, max_length=255)
    outcome_reason_code: str | None = Field(default=None, max_length=64)
    contains_phi: bool = Field(default=False)
    requires_compliance_review: bool = Field(default=False)
    intake_summary: dict | None = Field(default=None, sa_column=Column(JSON))
    created_by_user_id: str = Field(max_length=64, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class RfpMetadataRecord(SQLModel, table=True):
    __tablename__ = "rfp_metadata"

    rfp_id: str = Field(primary_key=True, max_length=64)
    ticket_id: str = Field(foreign_key="rfp_ticket.ticket_id", unique=True, index=True)
    client_name: str | None = None
    client_country: str | None = Field(default=None, max_length=8)
    program_type: str | None = Field(default=None, max_length=64)
    covered_population: int | None = None
    deadline: str | None = Field(default=None, max_length=64)
    budget_range: str | None = None
    departments_needed: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    currency: str | None = Field(default=None, max_length=8)
    flesch_reading_ease: float | None = None
    flesch_kincaid_grade: float | None = None
    gunning_fog: float | None = None
    word_count: int | None = None
    sentence_count: int | None = None
    character_count: int | None = None
    page_count: int | None = None
    metric_status: str | None = Field(default=None, max_length=64)
    classification_confidence: float | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    draft_content: str | None = None
    evaluation_results: dict | None = Field(default=None, sa_column=Column(JSON))
    approval_status: str | None = Field(default=None, max_length=32)
    approver: str | None = None
    approved_at: datetime | None = None


class RfpDepartmentSection(SQLModel, table=True):
    __tablename__ = "rfp_department_section"
    __table_args__ = (UniqueConstraint("ticket_id", "department_id"),)

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_ticket.ticket_id", index=True)
    department_id: str = Field(max_length=32)
    owner_name: str = Field(max_length=120)
    key_aspects: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    open_questions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    source_references: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    contains_phi: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    draft_content: str | None = None
    evaluation_results: dict | None = Field(default=None, sa_column=Column(JSON))
    approval_status: str | None = Field(default=None, max_length=32)
    approver: str | None = None
    approved_at: datetime | None = None
