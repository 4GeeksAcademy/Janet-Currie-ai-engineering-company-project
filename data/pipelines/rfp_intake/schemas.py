"""Structured RFP contracts. Department owners are application data, not model output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DepartmentId = Literal["revenue", "clinical", "compliance"]
DEPARTMENT_ORDER: tuple[DepartmentId, ...] = ("revenue", "clinical", "compliance")

DEPARTMENTS: dict[str, dict[str, str]] = {
    "revenue": {"name": "Revenue Cycle", "owner": "Tom Callahan"},
    "clinical": {"name": "Clinical Operations", "owner": "Dr. Marcus Reid"},
    "compliance": {
        "name": "Compliance and Data Governance",
        "owner": "Claire Whitfield",
    },
}

ProgramType = Literal[
    "occupational_health",
    "corporate_wellness",
    "referral_network",
    "other_institutional",
]
CountryCode = Literal["US", "UK"]
CurrencyCode = Literal["USD", "GBP"]

MAX_ASPECTS = 12
MAX_TEXT = 240


class Classification(BaseModel):
    is_rfp: bool
    reason_code: str = Field(max_length=80)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)
    missing_fields: list[str] = Field(default_factory=list, max_length=12)


class ExtractedMetadata(BaseModel):
    client_name: str | None = None
    client_country: str | None = None
    program_type: str | None = None
    covered_population: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    departments_needed: list[str] = Field(default_factory=list)


class ValidatedMetadata(BaseModel):
    client_name: str | None = None
    client_country: CountryCode | None = None
    program_type: ProgramType | None = None
    covered_population: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    departments_needed: list[DepartmentId]
    currency: CurrencyCode | None = None


class DepartmentResult(BaseModel):
    department_id: DepartmentId
    key_aspects: list[str] = Field(default_factory=list, max_length=MAX_ASPECTS)
    open_questions: list[str] = Field(default_factory=list, max_length=MAX_ASPECTS)
    source_references: list[str] = Field(default_factory=list, max_length=8)


class HandoffDepartment(BaseModel):
    department_id: DepartmentId
    owner: str
    key_aspects: list[str]
    open_questions: list[str]


class Handoff(BaseModel):
    ticket_id: str
    rfp_id: str
    client_country: CountryCode | None
    currency: CurrencyCode | None
    departments: list[HandoffDepartment]
    requires_compliance: bool
    contains_phi: bool


class Readability(BaseModel):
    flesch_reading_ease: float | None = None
    flesch_kincaid_grade: float | None = None
    gunning_fog: float | None = None
    word_count: int = 0
    sentence_count: int = 0
    character_count: int = 0
    page_count: int = 0
    metric_status: str = "ok"


def currency_for(country: str | None) -> CurrencyCode | None:
    if country == "US":
        return "USD"
    if country == "UK":
        return "GBP"
    return None


def select_departments(requested: list[str] | None = None) -> list[DepartmentId]:
    """Accepted RFPs always use the three known departments. Unknown ids are ignored."""

    del requested
    return list(DEPARTMENT_ORDER)


def _clean(value: str | None, limit: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    return text[:limit]


def normalize_metadata(raw: ExtractedMetadata | dict) -> ValidatedMetadata:
    data = raw if isinstance(raw, ExtractedMetadata) else ExtractedMetadata.model_validate(raw)
    country = data.client_country if data.client_country in {"US", "UK"} else None
    program = data.program_type if data.program_type in {
        "occupational_health",
        "corporate_wellness",
        "referral_network",
        "other_institutional",
    } else ("other_institutional" if _clean(data.program_type) else None)
    population = data.covered_population
    if population is not None and population < 0:
        population = None
    known = [item for item in data.departments_needed if item in DEPARTMENTS]
    departments = select_departments(known)
    return ValidatedMetadata(
        client_name=_clean(data.client_name),
        client_country=country,  # type: ignore[arg-type]
        program_type=program,  # type: ignore[arg-type]
        covered_population=population,
        deadline=_clean(data.deadline, 40),
        budget_range=_clean(data.budget_range),
        departments_needed=departments,
        currency=currency_for(country),
    )
