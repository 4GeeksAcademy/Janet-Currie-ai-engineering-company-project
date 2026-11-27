"""Typed graph state. Durable lifecycle lives on the ticket row, not a checkpointer."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class IntakeState(TypedDict, total=False):
    ticket_id: str
    raw_pdf_path: str
    rfp_id: str
    safe_markdown: str
    page_count: int
    contains_phi: bool
    privacy_reason_code: str | None
    requires_compliance_review: bool
    readability: dict | None
    metadata: dict | None
    classification: dict | None
    work_items: list
    department_results: Annotated[list, operator.add]
    handoff: dict | None
    outcome: str
    outcome_reason_code: str | None
    truncated: bool
    work_item: dict
