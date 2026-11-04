"""Normalize Celery states for GET /tasks/{task_id}."""

from __future__ import annotations

import re
from typing import Any

from kombu.exceptions import OperationalError

from app.celery_app import BrokerUnavailableError, celery_app, configure_celery, redis_url
from app.reporting.schemas import PipelineTaskResult, TaskStatusResponse

TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

CELERY_TO_PUBLIC = {
    "PENDING": "pending",
    "RECEIVED": "pending",
    "STARTED": "started",
    "RETRY": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "REVOKED": "failure",
}


class InvalidTaskIdError(ValueError):
    """Task id failed the public shape check."""


def public_status(celery_state: str | None) -> str:
    key = (celery_state or "PENDING").upper()
    return CELERY_TO_PUBLIC.get(key, "pending")


def validate_task_id(task_id: str) -> str:
    text = (task_id or "").strip()
    if not TASK_ID_RE.fullmatch(text):
        raise InvalidTaskIdError("task_id is malformed")
    return text


def _safe_result(raw: Any) -> PipelineTaskResult | None:
    if not isinstance(raw, dict):
        return None
    month = raw.get("month_start")
    return PipelineTaskResult(
        run_id=str(raw.get("run_id", "")),
        status=str(raw.get("status", "")),
        month_start=None if month in (None, "") else str(month),
        records_processed=int(raw.get("records_processed") or 0),
        events_extracted=int(raw.get("events_extracted") or 0),
        events_quarantined=int(raw.get("events_quarantined") or 0),
    )


def task_status(task_id: str) -> TaskStatusResponse:
    validated = validate_task_id(task_id)
    url = redis_url()
    if not url:
        raise BrokerUnavailableError("REDIS_URL is missing or malformed")
    configure_celery(celery_app, url=url)
    try:
        async_result = celery_app.AsyncResult(validated)
        state = async_result.state
        public = public_status(state)
        result = None
        if public == "success":
            result = _safe_result(async_result.result)
        return TaskStatusResponse(task_id=validated, status=public, result=result)
    except BrokerUnavailableError:
        raise
    except (OperationalError, ConnectionError, OSError, TimeoutError) as exc:
        raise BrokerUnavailableError("task result backend is unavailable") from exc
