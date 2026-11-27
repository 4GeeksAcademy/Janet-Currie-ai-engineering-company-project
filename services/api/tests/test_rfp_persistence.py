"""Ticket persistence and transactional completion."""

from __future__ import annotations

from sqlmodel import Session

from app.database import get_engine
from app.rfp.models import RfpTicket
from app.rfp.repository import (
    complete_intake,
    create_ticket,
    get_ticket,
    metadata_for,
    persist_completion,
    sections_for,
)
from tests.helpers import reset_inventory_db

HANDOFF = {
    "ticket_id": "ticket-1",
    "rfp_id": "rfp-1",
    "client_country": "US",
    "currency": "USD",
    "departments": [],
    "requires_compliance": True,
    "contains_phi": False,
}


def _payload():
    metadata = {
        "client_name": "Meridian Manufacturing, Inc.",
        "client_country": "US",
        "program_type": "occupational_health",
        "covered_population": 800,
        "deadline": "2026-08-23",
        "budget_range": None,
        "departments_needed": ["revenue", "clinical", "compliance"],
        "currency": "USD",
    }
    readability = {
        "flesch_reading_ease": 40.0,
        "flesch_kincaid_grade": 12.0,
        "gunning_fog": 14.0,
        "word_count": 120,
        "sentence_count": 8,
        "character_count": 700,
        "page_count": 2,
        "metric_status": "ok",
    }
    departments = [
        {
            "department_id": department_id,
            "key_aspects": [f"{department_id} fact"],
            "open_questions": ["What is missing?"],
            "source_references": ["Scope"],
        }
        for department_id in ("revenue", "clinical", "compliance")
    ]
    return metadata, readability, departments


def test_completion_is_idempotent_and_requires_every_section() -> None:
    reset_inventory_db()
    create_ticket(ticket_id="ticket-1", raw_pdf_path="data/raw/ticket-1.pdf", created_by_user_id="1")
    metadata, readability, departments = _payload()
    persist_completion(
        "ticket-1",
        rfp_id="rfp-1",
        metadata=metadata,
        readability=readability,
        departments=departments,
        handoff=HANDOFF,
        confidence=0.9,
    )
    persist_completion(
        "ticket-1",
        rfp_id="rfp-2",
        metadata=metadata,
        readability=readability,
        departments=departments,
        handoff=HANDOFF,
        confidence=0.9,
    )
    ticket = get_ticket("ticket-1")
    assert ticket is not None
    assert ticket.status == "intake_complete"
    assert ticket.rfp_id == "rfp-1"
    assert metadata_for("ticket-1") is not None
    assert len(sections_for("ticket-1")) == 3
    assert {row.department_id for row in sections_for("ticket-1")} == {
        "revenue",
        "clinical",
        "compliance",
    }


def test_rollback_leaves_the_ticket_analyzing() -> None:
    reset_inventory_db()
    create_ticket(ticket_id="ticket-2", raw_pdf_path="data/raw/ticket-2.pdf", created_by_user_id="1")
    metadata, readability, departments = _payload()
    with Session(get_engine()) as session:
        ticket = session.get(RfpTicket, "ticket-2")
        assert ticket is not None
        complete_intake(
            session,
            ticket,
            rfp_id="rfp-2",
            metadata=metadata,
            readability=readability,
            departments=departments,
            handoff=HANDOFF,
            confidence=None,
        )
        session.rollback()
    ticket = get_ticket("ticket-2")
    assert ticket is not None
    assert ticket.status == "analyzing"
    assert ticket.intake_summary is None
    assert metadata_for("ticket-2") is None
    assert sections_for("ticket-2") == []
