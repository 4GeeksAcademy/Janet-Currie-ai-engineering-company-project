"""Celery wrapper for RFP intake. The message carries only a ticket id."""

from __future__ import annotations

import logging
import time
from typing import Any

from celery.exceptions import Retry

from app.celery_app import (
    TASK_MAX_RETRIES,
    TASK_SOFT_TIME_LIMIT,
    TASK_TIME_LIMIT,
    BrokerUnavailableError,
    celery_app,
    configure_celery,
    require_redis_url,
)
from app.jobs.job_runner import sanitize_error
from app.rfp.repository import (
    get_ticket,
    mark_discarded,
    mark_failed,
    mark_retrying,
    mark_running,
    persist_completion,
)
from app.rfp.storage import UploadRejected, absolute_pdf_path
from app.tasks.pipeline_run import PermanentTaskError, retry_countdown
from app.tasks.store import record_exhausted_failure
from pipelines.rfp_intake.conversion import ConversionError
from pipelines.rfp_intake.llm import ModelCallError
from pipelines.rfp_intake.service import run_intake

logger = logging.getLogger("healthcore.rfp")

TASK_NAME_RFP = "app.tasks.rfp_intake.run_rfp_intake"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (PermanentTaskError, UploadRejected)):
        return False
    if isinstance(exc, (ConversionError, ModelCallError)):
        return exc.retryable
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def _fail(ticket_id: str, reason_code: str) -> None:
    safe = reason_code if reason_code in {"processing_failed", "conversion_failed"} else "processing_failed"
    mark_failed(ticket_id, safe)


def _persist_dlq(task_id: str, attempt_number: int, error: str) -> None:
    record_exhausted_failure(
        task_id=str(task_id),
        task_name=TASK_NAME_RFP,
        attempt_number=attempt_number,
        error_message=sanitize_error(error),
    )


@celery_app.task(
    bind=True,
    name=TASK_NAME_RFP,
    acks_late=True,
    max_retries=TASK_MAX_RETRIES,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    time_limit=TASK_TIME_LIMIT,
)
def run_rfp_intake(self, ticket_id: str) -> dict[str, Any]:
    task_id = str(getattr(self.request, "id", "") or "")
    retries = int(getattr(self.request, "retries", 0) or 0)
    attempt = retries + 1
    started = time.monotonic()
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise PermanentTaskError("missing_ticket")
    if ticket.status == "intake_complete":
        return {"ticket_id": ticket_id, "status": "intake_complete"}
    mark_running(ticket_id)
    try:
        path = absolute_pdf_path(ticket.raw_pdf_path)
        result = run_intake(ticket_id=ticket_id, raw_pdf_path=str(path), rfp_id=ticket.rfp_id)
        if result.outcome == "discarded":
            mark_discarded(
                ticket_id,
                reason_code=result.reason_code or "not_an_rfp",
                contains_phi=result.contains_phi,
                requires_compliance_review=result.requires_compliance_review,
            )
            logger.info("rfp_intake_discarded ticket_id=%s reason=%s", ticket_id, result.reason_code)
            return {"ticket_id": ticket_id, "status": "discarded"}
        if result.outcome == "intake_complete" and result.handoff and result.metadata and result.readability:
            handoff = dict(result.handoff)
            handoff["ticket_id"] = ticket_id
            confidence = None
            if result.classification:
                confidence = result.classification.get("confidence")
            persist_completion(
                ticket_id,
                rfp_id=result.rfp_id or handoff.get("rfp_id") or ticket_id,
                metadata=result.metadata,
                readability=result.readability,
                departments=result.departments,
                handoff=handoff,
                confidence=confidence,
            )
            logger.info("rfp_intake_complete ticket_id=%s", ticket_id)
            return {"ticket_id": ticket_id, "status": "intake_complete"}
        _fail(ticket_id, result.reason_code or "processing_failed")
        raise PermanentTaskError("processing_failed")
    except Retry:
        raise
    except PermanentTaskError as exc:
        _persist_dlq(task_id, attempt, sanitize_error(exc))
        raise
    except (ConversionError, ModelCallError) as exc:
        if exc.retryable and retries < TASK_MAX_RETRIES:
            mark_retrying(ticket_id)
            raise self.retry(exc=exc, countdown=retry_countdown(retries)) from exc
        _fail(ticket_id, exc.reason_code)
        _persist_dlq(task_id, attempt, exc.reason_code)
        raise PermanentTaskError(exc.reason_code) from exc
    except Exception as exc:
        error = sanitize_error(exc)
        if _is_retryable(exc) and retries < TASK_MAX_RETRIES:
            mark_retrying(ticket_id)
            logger.info(
                "rfp_intake_retry ticket_id=%s attempt=%s duration_ms=%.1f",
                ticket_id,
                attempt,
                (time.monotonic() - started) * 1000,
            )
            raise self.retry(exc=exc, countdown=retry_countdown(retries)) from exc
        _fail(ticket_id, "processing_failed")
        _persist_dlq(task_id, attempt, error)
        raise


def enqueue_rfp_intake(ticket_id: str) -> str:
    url = require_redis_url()
    configure_celery(celery_app, url=url)
    try:
        result = run_rfp_intake.apply_async(args=[ticket_id])
    except Exception as exc:
        raise BrokerUnavailableError("task broker is unavailable") from exc
    if result.id is None:
        raise BrokerUnavailableError("task broker did not return a task id")
    logger.info("published task_name=%s task_id=%s", TASK_NAME_RFP, result.id)
    return str(result.id)
