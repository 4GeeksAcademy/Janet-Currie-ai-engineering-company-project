"""Upload intake. Conversion and model calls stay in the worker."""

from __future__ import annotations

import logging
from uuid import uuid4

from app.celery_app import BrokerUnavailableError
from app.rfp.repository import (
    TicketConflict,
    attach_task,
    create_ticket,
    mark_queue_failed,
    prepare_reprocess,
)
from app.rfp.storage import (
    UploadRejected,
    declared_too_large,
    delete_stored,
    filename_allowed,
    save_pdf,
)

logger = logging.getLogger("healthcore.rfp")


class QueuePublishError(RuntimeError):
    def __init__(self, ticket_id: str) -> None:
        super().__init__("queue_unavailable")
        self.ticket_id = ticket_id


def accept_pdf(
    *,
    filename: str | None,
    content_type: str | None,
    content_length: str | None,
    chunks,
    created_by_user_id: str,
    max_bytes: int | None = None,
) -> dict:
    if not filename_allowed(filename):
        raise UploadRejected("bad_extension")
    if (content_type or "").split(";", 1)[0].strip().lower() != "application/pdf":
        raise UploadRejected("bad_type")
    if declared_too_large(content_length, max_bytes):
        raise UploadRejected("too_large")
    ticket_id = str(uuid4())
    relative = save_pdf(ticket_id, chunks, max_bytes=max_bytes)
    try:
        create_ticket(
            ticket_id=ticket_id,
            raw_pdf_path=relative,
            created_by_user_id=created_by_user_id,
        )
    except Exception:
        delete_stored(relative)
        raise
    try:
        from app.tasks.rfp_intake import enqueue_rfp_intake

        task_id = enqueue_rfp_intake(ticket_id)
    except BrokerUnavailableError:
        failed = mark_queue_failed(ticket_id)
        logger.info("rfp_enqueue_failed ticket_id=%s", ticket_id)
        raise QueuePublishError(failed.ticket_id) from None
    attach_task(ticket_id, task_id)
    logger.info("rfp_ticket_queued ticket_id=%s", ticket_id)
    return {
        "ticket_id": ticket_id,
        "status": "analyzing",
        "processing_state": "queued",
    }


def reprocess_ticket(ticket_id: str) -> dict:
    try:
        prepare_reprocess(ticket_id)
    except TicketConflict as exc:
        raise TicketConflict("busy") from exc
    try:
        from app.tasks.rfp_intake import enqueue_rfp_intake

        task_id = enqueue_rfp_intake(ticket_id)
    except BrokerUnavailableError:
        mark_queue_failed(ticket_id)
        raise QueuePublishError(ticket_id) from None
    attach_task(ticket_id, task_id)
    return {
        "ticket_id": ticket_id,
        "status": "analyzing",
        "processing_state": "queued",
    }
