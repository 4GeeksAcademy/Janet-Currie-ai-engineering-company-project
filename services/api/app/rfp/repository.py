"""Transactional ticket reads and guarded status changes."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.database import get_engine
from app.rfp.models import RfpDepartmentSection, RfpMetadataRecord, RfpTicket, utcnow
from pipelines.rfp_intake.schemas import DEPARTMENTS

ACTIVE_PROCESSING = frozenset({"queued", "running", "retrying"})


class TicketConflict(RuntimeError):
    pass


class TicketNotFound(RuntimeError):
    pass


def _session() -> Session:
    return Session(get_engine())


def _touch(row: RfpTicket) -> None:
    row.updated_at = datetime.now(timezone.utc)


def create_ticket(*, ticket_id: str, raw_pdf_path: str, created_by_user_id: str) -> RfpTicket:
    row = RfpTicket(
        ticket_id=ticket_id,
        status="analyzing",
        processing_state="queued",
        raw_pdf_path=raw_pdf_path,
        created_by_user_id=created_by_user_id,
    )
    with _session() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
        return row


def get_ticket(ticket_id: str) -> RfpTicket | None:
    with _session() as session:
        row = session.get(RfpTicket, ticket_id)
        if row is not None:
            session.expunge(row)
        return row


def list_tickets(*, limit: int, offset: int) -> list[tuple[RfpTicket, RfpMetadataRecord | None]]:
    with _session() as session:
        rows = session.exec(
            select(RfpTicket).order_by(col(RfpTicket.created_at).desc()).offset(offset).limit(limit)
        ).all()
        pairs = []
        for ticket in rows:
            meta = session.exec(
                select(RfpMetadataRecord).where(RfpMetadataRecord.ticket_id == ticket.ticket_id)
            ).first()
            session.expunge(ticket)
            if meta is not None:
                session.expunge(meta)
            pairs.append((ticket, meta))
        return pairs


def attach_task(ticket_id: str, task_id: str) -> None:
    with _session() as session:
        row = session.get(RfpTicket, ticket_id)
        if row is None:
            raise TicketNotFound(ticket_id)
        row.task_id = task_id
        _touch(row)
        session.add(row)
        session.commit()


def mark_queue_failed(ticket_id: str) -> RfpTicket:
    with _session() as session:
        row = _require(session, ticket_id)
        row.processing_state = "failed"
        row.outcome_reason_code = "processing_failed"
        row.status = "analyzing"
        _touch(row)
        session.add(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
        return row


def mark_running(ticket_id: str) -> None:
    _set_processing(ticket_id, "running")


def mark_retrying(ticket_id: str) -> None:
    _set_processing(ticket_id, "retrying")


def _set_processing(ticket_id: str, state: str) -> None:
    with _session() as session:
        row = _require(session, ticket_id)
        if row.status == "intake_complete":
            return
        row.processing_state = state
        row.status = "analyzing"
        _touch(row)
        session.add(row)
        session.commit()


def mark_discarded(
    ticket_id: str,
    *,
    reason_code: str,
    contains_phi: bool,
    requires_compliance_review: bool,
) -> None:
    with _session() as session:
        row = _require(session, ticket_id)
        if row.status == "intake_complete":
            raise TicketConflict("complete")
        row.status = "discarded"
        row.processing_state = "succeeded"
        row.outcome_reason_code = reason_code
        row.contains_phi = contains_phi
        row.requires_compliance_review = requires_compliance_review
        row.intake_summary = None
        row.rfp_id = None
        _touch(row)
        session.add(row)
        session.commit()


def mark_failed(ticket_id: str, reason_code: str = "processing_failed") -> None:
    with _session() as session:
        row = _require(session, ticket_id)
        if row.status == "intake_complete":
            return
        row.status = "analyzing"
        row.processing_state = "failed"
        row.outcome_reason_code = reason_code
        _touch(row)
        session.add(row)
        session.commit()


def prepare_reprocess(ticket_id: str) -> RfpTicket:
    with _session() as session:
        row = _require(session, ticket_id)
        if row.status == "intake_complete" or row.processing_state in ACTIVE_PROCESSING:
            raise TicketConflict("busy")
        row.status = "analyzing"
        row.processing_state = "queued"
        row.outcome_reason_code = None
        row.contains_phi = False
        row.requires_compliance_review = False
        row.intake_summary = None
        _touch(row)
        session.add(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
        return row


def complete_intake(
    session: Session,
    ticket: RfpTicket,
    *,
    rfp_id: str,
    metadata: dict,
    readability: dict,
    departments: list[dict],
    handoff: dict,
    confidence: float | None,
) -> None:
    if ticket.status == "intake_complete":
        return
    if len(departments) != 3 or handoff is None or metadata is None:
        raise TicketConflict("incomplete")
    ids = [item["department_id"] for item in departments]
    if set(ids) != {"revenue", "clinical", "compliance"} or len(ids) != 3:
        raise TicketConflict("incomplete")
    existing = session.exec(
        select(RfpMetadataRecord).where(RfpMetadataRecord.ticket_id == ticket.ticket_id)
    ).first()
    record = existing or RfpMetadataRecord(rfp_id=rfp_id, ticket_id=ticket.ticket_id)
    record.rfp_id = existing.rfp_id if existing is not None else rfp_id
    record.client_name = metadata.get("client_name")
    record.client_country = metadata.get("client_country")
    record.program_type = metadata.get("program_type")
    record.covered_population = metadata.get("covered_population")
    record.deadline = metadata.get("deadline")
    record.budget_range = metadata.get("budget_range")
    record.departments_needed = list(metadata.get("departments_needed") or [])
    record.currency = metadata.get("currency")
    record.flesch_reading_ease = readability.get("flesch_reading_ease")
    record.flesch_kincaid_grade = readability.get("flesch_kincaid_grade")
    record.gunning_fog = readability.get("gunning_fog")
    record.word_count = readability.get("word_count")
    record.sentence_count = readability.get("sentence_count")
    record.character_count = readability.get("character_count")
    record.page_count = readability.get("page_count")
    record.metric_status = readability.get("metric_status")
    record.classification_confidence = confidence
    record.updated_at = utcnow()
    session.add(record)
    previous = session.exec(
        select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == ticket.ticket_id)
    ).all()
    for section in previous:
        session.delete(section)
    session.flush()
    for item in departments:
        department_id = item["department_id"]
        session.add(
            RfpDepartmentSection(
                ticket_id=ticket.ticket_id,
                department_id=department_id,
                owner_name=DEPARTMENTS[department_id]["owner"],
                key_aspects=list(item.get("key_aspects") or []),
                open_questions=list(item.get("open_questions") or []),
                source_references=list(item.get("source_references") or []),
                contains_phi=False,
            )
        )
    ticket.rfp_id = record.rfp_id
    ticket.intake_summary = handoff
    ticket.status = "intake_complete"
    ticket.processing_state = "succeeded"
    ticket.outcome_reason_code = None
    ticket.contains_phi = False
    ticket.requires_compliance_review = False
    _touch(ticket)
    session.add(ticket)


def persist_completion(
    ticket_id: str,
    *,
    rfp_id: str,
    metadata: dict,
    readability: dict,
    departments: list[dict],
    handoff: dict,
    confidence: float | None,
) -> None:
    with _session() as session:
        ticket = _require(session, ticket_id)
        try:
            complete_intake(
                session,
                ticket,
                rfp_id=rfp_id,
                metadata=metadata,
                readability=readability,
                departments=departments,
                handoff=handoff,
                confidence=confidence,
            )
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise TicketConflict("duplicate") from exc


def sections_for(ticket_id: str) -> list[RfpDepartmentSection]:
    with _session() as session:
        rows = session.exec(
            select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == ticket_id)
        ).all()
        for row in rows:
            session.expunge(row)
        return list(rows)


def metadata_for(ticket_id: str) -> RfpMetadataRecord | None:
    with _session() as session:
        row = session.exec(
            select(RfpMetadataRecord).where(RfpMetadataRecord.ticket_id == ticket_id)
        ).first()
        if row is not None:
            session.expunge(row)
        return row


def _require(session: Session, ticket_id: str) -> RfpTicket:
    row = session.get(RfpTicket, ticket_id)
    if row is None:
        raise TicketNotFound(ticket_id)
    return row
