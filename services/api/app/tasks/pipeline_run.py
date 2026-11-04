"""Clinic-supply pipeline as a Celery task. Thin wrapper around execute_."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
from celery.exceptions import Retry, SoftTimeLimitExceeded, TimeLimitExceeded
from kombu.exceptions import OperationalError

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
from app.tasks.store import TASK_NAME_PIPELINE, record_exhausted_failure

logger = logging.getLogger(__name__)

ExecuteFn = Callable[[date | None], dict[str, Any]]
_execute_fn: ExecuteFn | None = None


class PermanentTaskError(ValueError):
    """Invalid task input; do not retry."""


def set_execute(fn: ExecuteFn | None) -> None:
    global _execute_fn
    _execute_fn = fn


def reset_execute() -> None:
    set_execute(None)


def retry_countdown(retries: int) -> int:
    return min(60, 5 * (2 ** retries))


def parse_month_start(raw: str | None) -> date | None:
    if raw is None or str(raw).strip() == "":
        return None
    text = str(raw).strip()
    try:
        value = date.fromisoformat(text)
    except ValueError as exc:
        raise PermanentTaskError(
            f"month_start must be YYYY-MM-DD, got {text!r}"
        ) from exc
    if value.day != 1:
        raise PermanentTaskError("month_start must be the first day of a month")
    return value


def _run_execute(month_start: date | None) -> dict[str, Any]:
    if _execute_fn is not None:
        return _execute_fn(month_start)
    from pipelines.pipeline import execute_monthly_clinic_supply_performance

    return execute_monthly_clinic_supply_performance(month_start)


def _is_retryable(exc: BaseException) -> bool:
    from pipelines.pipeline import PipelineBusyError

    if isinstance(exc, PermanentTaskError):
        return False
    return isinstance(
        exc,
        (
            PipelineBusyError,
            httpx.HTTPError,
            OSError,
            TimeoutError,
            ConnectionError,
            SoftTimeLimitExceeded,
            TimeLimitExceeded,
            OperationalError,
        ),
    )


def _attempt_number(retries: int | None) -> int:
    return int(retries or 0) + 1


def _bounded_result(record: dict[str, Any], month_start: date | None) -> dict[str, Any]:
    return {
        "run_id": str(record.get("run_id", "")),
        "status": str(record.get("status", "")),
        "month_start": month_start.isoformat() if month_start else None,
        "records_processed": int(record.get("records_processed") or 0),
        "events_extracted": int(record.get("events_extracted") or 0),
        "events_quarantined": int(record.get("events_quarantined") or 0),
    }


def _log_attempt(
    *,
    task_id: str,
    attempt_number: int,
    status: str,
    duration_ms: float,
    run_id: str | None = None,
    error: str | None = None,
) -> None:
    extra = f" run_id={run_id}" if run_id else ""
    err = f" error={error}" if error else ""
    logger.info(
        "task_name=%s task_id=%s attempt_number=%s status=%s duration_ms=%.1f%s%s",
        TASK_NAME_PIPELINE,
        task_id,
        attempt_number,
        status,
        duration_ms,
        extra,
        err,
    )


def _persist_dlq(task_id: str, attempt_number: int, error: str) -> None:
    record_exhausted_failure(
        task_id=str(task_id),
        task_name=TASK_NAME_PIPELINE,
        attempt_number=attempt_number,
        error_message=error,
    )


@celery_app.task(
    bind=True,
    name=TASK_NAME_PIPELINE,
    acks_late=True,
    max_retries=TASK_MAX_RETRIES,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    time_limit=TASK_TIME_LIMIT,
)
def run_clinic_supply_pipeline(self, month_start: str | None = None) -> dict[str, Any]:
    task_id = str(getattr(self.request, "id", "") or "")
    retries = int(getattr(self.request, "retries", 0) or 0)
    attempt_number = _attempt_number(retries)
    started = time.monotonic()
    run_id: str | None = None
    target: date | None = None
    try:
        target = parse_month_start(month_start)
        record = _run_execute(target)
        run_id = str(record.get("run_id", "") or "") or None
        result = _bounded_result(record, target)
        _log_attempt(
            task_id=task_id,
            attempt_number=attempt_number,
            status="success",
            duration_ms=(time.monotonic() - started) * 1000,
            run_id=run_id,
        )
        return result
    except Retry:
        raise
    except PermanentTaskError as exc:
        error = sanitize_error(exc)
        _log_attempt(
            task_id=task_id,
            attempt_number=attempt_number,
            status="failure",
            duration_ms=(time.monotonic() - started) * 1000,
            error=error,
        )
        _persist_dlq(task_id, attempt_number, error)
        raise
    except Exception as exc:
        error = sanitize_error(exc)
        duration_ms = (time.monotonic() - started) * 1000
        if _is_retryable(exc) and retries < TASK_MAX_RETRIES:
            countdown = retry_countdown(retries)
            _log_attempt(
                task_id=task_id,
                attempt_number=attempt_number,
                status="retry",
                duration_ms=duration_ms,
                run_id=run_id,
                error=error,
            )
            raise self.retry(exc=exc, countdown=countdown) from exc
        _log_attempt(
            task_id=task_id,
            attempt_number=attempt_number,
            status="failure",
            duration_ms=duration_ms,
            run_id=run_id,
            error=error,
        )
        _persist_dlq(task_id, attempt_number, error)
        raise


def enqueue_pipeline_run(month_start: str | None) -> str:
    try:
        url = require_redis_url()
    except BrokerUnavailableError:
        raise
    configure_celery(celery_app, url=url)
    try:
        result = run_clinic_supply_pipeline.apply_async(kwargs={"month_start": month_start})
    except Exception as exc:
        raise BrokerUnavailableError("task broker is unavailable") from exc
    if result.id is None:
        raise BrokerUnavailableError("task broker did not return a task id")
    logger.info(
        "published task_name=%s task_id=%s month_start=%s",
        TASK_NAME_PIPELINE,
        result.id,
        month_start,
    )
    return str(result.id)
