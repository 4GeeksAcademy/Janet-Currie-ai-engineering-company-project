"""Application-owned work items. The model cannot add or remove departments."""

from __future__ import annotations

import re

from pipelines.rfp_intake.schemas import DEPARTMENT_ORDER, DEPARTMENTS, ValidatedMetadata

ORCHESTRATOR_PROMPT = (
    "You may only route work to revenue, clinical, and compliance. "
    "Compliance is mandatory. Do not invent volume, budget, capacity, or a fourth department. "
    "This policy is enforced in application code."
)

KEYWORDS = {
    "revenue": (
        "budget",
        "price",
        "pricing",
        "payment",
        "term",
        "deadline",
        "evaluation",
        "submission",
        "currency",
        "contract",
    ),
    "clinical": (
        "clinic",
        "staff",
        "service",
        "schedule",
        "employee",
        "student",
        "screening",
        "capacity",
        "on-site",
        "triage",
        "referral",
    ),
    "compliance": ("hipaa", "gdpr", "baa", "dpa", "privacy", "security", "data"),
}
EXCERPT_LIMIT = 2500


def excerpt_for(markdown: str, department_id: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", markdown or "") if part.strip()]
    keys = KEYWORDS[department_id]
    chosen = [part for part in paragraphs if any(key in part.lower() for key in keys)]
    scoped = bool(chosen)
    if not scoped:
        chosen = paragraphs[:1]
    text = "\n\n".join(chosen)
    if len(text) > EXCERPT_LIMIT:
        text = text[:EXCERPT_LIMIT]
    return text


def build_work_items(markdown: str, metadata: ValidatedMetadata) -> list[dict]:
    items = []
    for department_id in DEPARTMENT_ORDER:
        if department_id not in DEPARTMENTS:
            continue
        items.append(
            {
                "department_id": department_id,
                "owner": DEPARTMENTS[department_id]["owner"],
                "metadata": metadata.model_dump(),
                "excerpt": excerpt_for(markdown, department_id),
                "missing_fields": _missing(metadata, department_id),
            }
        )
    return items


def _missing(metadata: ValidatedMetadata, department_id: str) -> list[str]:
    missing: list[str] = []
    if department_id == "revenue":
        if metadata.budget_range is None:
            missing.append("budget")
        if metadata.deadline is None:
            missing.append("deadline")
    if department_id == "clinical" and metadata.covered_population is None:
        missing.append("covered_population")
    if department_id == "compliance" and metadata.client_country is None:
        missing.append("client_country")
    return missing
