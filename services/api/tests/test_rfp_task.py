"""RFP Celery task outcomes stay truthful."""

from __future__ import annotations

import pytest
from celery.exceptions import Retry

from app.rfp.repository import create_ticket, get_ticket
from app.tasks.rfp_intake import run_rfp_intake
from app.tasks.store import MemoryDeadLetterStore, set_store
from pipelines.rfp_intake.llm import ModelCallError
from pipelines.rfp_intake.service import IntakeResult
from tests.helpers import reset_inventory_db


def _ticket() -> str:
    reset_inventory_db()
    create_ticket(ticket_id="ticket-task", raw_pdf_path="data/raw/ticket-task.pdf", created_by_user_id="4")
    return "ticket-task"


def test_discarded_classification_is_not_a_task_failure(monkeypatch) -> None:
    ticket_id = _ticket()
    store = MemoryDeadLetterStore()
    set_store(store)

    def fake_run(**_kwargs):
        return IntakeResult(
            outcome="discarded",
            reason_code="not_an_rfp",
            contains_phi=False,
            requires_compliance_review=False,
        )

    monkeypatch.setattr("app.tasks.rfp_intake.run_intake", fake_run)
    run_rfp_intake.push_request(id="task-discard", retries=0)
    try:
        result = run_rfp_intake.run(ticket_id)
    finally:
        run_rfp_intake.pop_request()
    assert result["status"] == "discarded"
    ticket = get_ticket(ticket_id)
    assert ticket is not None
    assert ticket.status == "discarded"
    assert ticket.outcome_reason_code == "not_an_rfp"
    assert store.rows == {}


def test_exhausted_failure_is_not_labeled_as_not_an_rfp(monkeypatch) -> None:
    ticket_id = _ticket()
    store = MemoryDeadLetterStore()
    set_store(store)

    def explode(**_kwargs):
        raise ModelCallError("processing_failed", retryable=True)

    monkeypatch.setattr("app.tasks.rfp_intake.run_intake", explode)
    run_rfp_intake.push_request(id="task-fail", retries=3)
    try:
        with pytest.raises(Exception):
            run_rfp_intake.run(ticket_id)
    finally:
        run_rfp_intake.pop_request()
    ticket = get_ticket(ticket_id)
    assert ticket is not None
    assert ticket.status == "analyzing"
    assert ticket.processing_state == "failed"
    assert ticket.outcome_reason_code == "processing_failed"
    assert ticket.outcome_reason_code != "not_an_rfp"
    assert store.get_by_task_id("task-fail") is not None


def test_retryable_failure_keeps_the_same_ticket(monkeypatch) -> None:
    ticket_id = _ticket()

    def explode(**_kwargs):
        raise TimeoutError("slow")

    def fake_retry(exc=None, countdown=None, **_kwargs):
        raise Retry(exc=exc, when=countdown)

    monkeypatch.setattr("app.tasks.rfp_intake.run_intake", explode)
    monkeypatch.setattr(run_rfp_intake, "retry", fake_retry)
    run_rfp_intake.push_request(id="task-retry", retries=0)
    try:
        with pytest.raises(Retry):
            run_rfp_intake.run(ticket_id)
    finally:
        run_rfp_intake.pop_request()
    ticket = get_ticket(ticket_id)
    assert ticket is not None
    assert ticket.ticket_id == ticket_id
    assert ticket.processing_state == "retrying"
    assert ticket.status == "analyzing"
