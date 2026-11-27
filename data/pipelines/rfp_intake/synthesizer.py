"""Assemble the Part 2 handoff from validated worker results."""

from __future__ import annotations

import re

from pipelines.rfp_intake.privacy import inspect_text
from pipelines.rfp_intake.schemas import (
    DEPARTMENT_ORDER,
    DEPARTMENTS,
    Handoff,
    HandoffDepartment,
    ValidatedMetadata,
)

SYNTHESIZER_PROMPT = (
    "Combine the department results into one intake handoff. "
    "Keep every required department once, use the fixed owner, and preserve disagreements "
    "as open questions. Do not write proposal prose, add a department, or invent facts. "
    "This assembly is enforced in application code."
)

_POPULATION = re.compile(r"(\d[\d,]*)\s+(?:employees|students)", re.IGNORECASE)
_MONEY = re.compile(r"[$£]\s?\d")


class HandoffRejected(ValueError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def build_handoff(
    *,
    ticket_id: str,
    rfp_id: str,
    metadata: ValidatedMetadata,
    results: list[dict],
    excerpts: dict[str, str],
) -> Handoff:
    ids = [item.get("department_id") for item in results]
    if len(ids) != len(set(ids)):
        raise HandoffRejected("duplicate_department")
    if any(item not in DEPARTMENTS for item in ids):
        raise HandoffRejected("unknown_department")
    if "compliance" not in ids or set(ids) != set(DEPARTMENT_ORDER):
        raise HandoffRejected("missing_compliance")
    _reject_phi(results)
    _reject_unsupported(results, excerpts)
    conflict = _population_conflict(results)
    ordered = []
    for department_id in DEPARTMENT_ORDER:
        match = next(item for item in results if item["department_id"] == department_id)
        questions = list(match.get("open_questions") or [])
        if conflict and conflict not in questions:
            questions.append(conflict)
        ordered.append(
            HandoffDepartment(
                department_id=department_id,  # type: ignore[arg-type]
                owner=DEPARTMENTS[department_id]["owner"],
                key_aspects=list(match.get("key_aspects") or []),
                open_questions=questions,
            )
        )
    handoff = Handoff(
        ticket_id=ticket_id,
        rfp_id=rfp_id,
        client_country=metadata.client_country,
        currency=metadata.currency,
        departments=ordered,
        requires_compliance=True,
        contains_phi=False,
    )
    if handoff.contains_phi:
        raise HandoffRejected("phi")
    return handoff


def _reject_phi(results: list[dict]) -> None:
    for item in results:
        blob = " ".join(
            list(item.get("key_aspects") or [])
            + list(item.get("open_questions") or [])
            + list(item.get("source_references") or [])
        )
        if inspect_text(blob).contains_phi:
            raise HandoffRejected("phi")


def _reject_unsupported(results: list[dict], excerpts: dict[str, str]) -> None:
    for item in results:
        excerpt = (excerpts.get(item["department_id"]) or "").lower()
        for aspect in item.get("key_aspects") or []:
            if _MONEY.search(aspect) and metadata_amount_missing(excerpt, aspect):
                raise HandoffRejected("unsupported_fact")


def metadata_amount_missing(excerpt: str, aspect: str) -> bool:
    amounts = re.findall(r"\d[\d,]*", aspect)
    return any(amount not in excerpt for amount in amounts)


def _population_conflict(results: list[dict]) -> str | None:
    found: set[str] = set()
    for item in results:
        for aspect in item.get("key_aspects") or []:
            match = _POPULATION.search(aspect)
            if match:
                found.add(match.group(1).replace(",", ""))
    if len(found) > 1:
        return "Department notes disagree on the covered population. Confirm the figure before drafting."
    return None
