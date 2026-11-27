"""Authenticated RFP ticket routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from app.auth.security import get_current_user
from app.rfp.repository import (
    TicketConflict,
    TicketNotFound,
    get_ticket,
    list_tickets,
    metadata_for,
    sections_for,
)
from app.rfp.schemas import (
    DepartmentView,
    MetadataView,
    ReadabilityView,
    TicketAccepted,
    TicketDetail,
    TicketListResponse,
    TicketSummary,
    safe_message,
)
from app.rfp.service import QueuePublishError, accept_pdf, reprocess_ticket
from app.rfp.storage import UploadRejected, declared_too_large
from pipelines.rfp_intake.schemas import DEPARTMENTS

router = APIRouter(prefix="/rfp", tags=["rfp"])

_UPLOAD_MESSAGES = {
    "bad_extension": "Upload a single PDF.",
    "bad_type": "Upload a single PDF.",
    "too_large": "That PDF is too large.",
    "empty": "The PDF is empty.",
    "bad_signature": "Upload a valid PDF.",
    "unsafe_path": "Upload a single PDF.",
}


@router.post("/tickets", response_model=TicketAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_rfp_ticket(
    request: Request,
    user: dict = Depends(get_current_user),
) -> TicketAccepted | JSONResponse:
    if declared_too_large(request.headers.get("content-length")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_UPLOAD_MESSAGES["too_large"])
    form = await request.form()
    uploads = [item for item in form.values() if isinstance(item, UploadFile)]
    if len(uploads) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_UPLOAD_MESSAGES["bad_extension"])
    upload = uploads[0]
    try:
        payload = accept_pdf(
            filename=upload.filename,
            content_type=upload.content_type,
            content_length=None,
            chunks=_chunks(upload),
            created_by_user_id=str(user["id"]),
        )
    except UploadRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_UPLOAD_MESSAGES.get(exc.reason_code, _UPLOAD_MESSAGES["bad_extension"]),
        ) from None
    except QueuePublishError as exc:
        body = TicketAccepted(
            ticket_id=exc.ticket_id,
            status="analyzing",
            processing_state="failed",
        )
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump())
    return TicketAccepted(**payload)


@router.get("/tickets", response_model=TicketListResponse)
def get_rfp_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(get_current_user),
) -> TicketListResponse:
    items = []
    for ticket, meta in list_tickets(limit=limit, offset=offset):
        items.append(
            TicketSummary(
                ticket_id=ticket.ticket_id,
                status=ticket.status,
                processing_state=ticket.processing_state,
                client_name=None if meta is None else meta.client_name,
                client_country=None if meta is None else meta.client_country,
                program_type=None if meta is None else meta.program_type,
                outcome_reason_code=ticket.outcome_reason_code,
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
            )
        )
    return TicketListResponse(items=items, limit=limit, offset=offset)


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
def get_rfp_ticket(ticket_id: str, _user: dict = Depends(get_current_user)) -> TicketDetail:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return _detail(ticket)


@router.post(
    "/tickets/{ticket_id}/reprocess",
    response_model=TicketAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def reprocess_rfp_ticket(
    ticket_id: str,
    _user: dict = Depends(get_current_user),
) -> TicketAccepted | JSONResponse:
    if get_ticket(ticket_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    try:
        payload = reprocess_ticket(ticket_id)
    except TicketNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from None
    except TicketConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket cannot be reprocessed.",
        ) from None
    except QueuePublishError as exc:
        body = TicketAccepted(
            ticket_id=exc.ticket_id,
            status="analyzing",
            processing_state="failed",
        )
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump())
    return TicketAccepted(**payload)


def _chunks(upload: UploadFile):
    while True:
        chunk = upload.file.read(64 * 1024)
        if not chunk:
            break
        yield chunk


def _detail(ticket) -> TicketDetail:
    meta = metadata_for(ticket.ticket_id) if ticket.status == "intake_complete" else None
    sections = sections_for(ticket.ticket_id) if ticket.status == "intake_complete" else []
    metadata = None
    if meta is not None:
        metadata = MetadataView(
            rfp_id=meta.rfp_id,
            client_name=meta.client_name,
            client_country=meta.client_country,
            program_type=meta.program_type,
            covered_population=meta.covered_population,
            deadline=meta.deadline,
            budget_range=meta.budget_range,
            departments_needed=list(meta.departments_needed or []),
            currency=meta.currency,
            classification_confidence=meta.classification_confidence,
            readability=ReadabilityView(
                flesch_reading_ease=meta.flesch_reading_ease,
                flesch_kincaid_grade=meta.flesch_kincaid_grade,
                gunning_fog=meta.gunning_fog,
                word_count=meta.word_count,
                sentence_count=meta.sentence_count,
                character_count=meta.character_count,
                page_count=meta.page_count,
                metric_status=meta.metric_status,
            ),
        )
    departments = []
    for section in sorted(sections, key=lambda row: ("revenue", "clinical", "compliance").index(row.department_id)):
        info = DEPARTMENTS[section.department_id]
        departments.append(
            DepartmentView(
                department_id=section.department_id,
                department_name=info["name"],
                owner_name=info["owner"],
                key_aspects=list(section.key_aspects or []),
                open_questions=list(section.open_questions or []),
            )
        )
    return TicketDetail(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        processing_state=ticket.processing_state,
        outcome_reason_code=ticket.outcome_reason_code,
        message=safe_message(ticket.status, ticket.processing_state, ticket.outcome_reason_code),
        contains_phi=bool(ticket.contains_phi),
        requires_compliance_review=bool(ticket.requires_compliance_review),
        metadata=metadata,
        departments=departments,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )
