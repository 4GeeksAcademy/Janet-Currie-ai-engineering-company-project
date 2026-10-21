"""job_runs status machine for the nightly telemetry export."""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

JOB_NAME = "nightly_export"
PENDING = "pending"
PROCESSING = "processing"
COMPLETED = "completed"
FAILED = "failed"
TERMINAL = frozenset({COMPLETED, FAILED})
ERROR_MAX = 400
SECRET_RE = re.compile(
    r"(?i)(password|secret|token|authorization|apikey|api_key|bearer\s+\S+|postgres(ql)?://\S+)"
)

class JobOverlapError(Exception):
    """Another nightly_export row is already processing."""


class JobStateError(Exception):
    """Illegal status transition or missing row."""


class InvalidTargetDateError(ValueError):
    """TARGET_DATE is missing, malformed, or not a real calendar date."""


class JobStore(Protocol):
    def insert(self, row: dict[str, Any]) -> dict[str, Any]: ...

    def update(self, run_id: str, fields: dict[str, Any]) -> dict[str, Any]: ...

    def list_processing(self, job_name: str) -> list[dict[str, Any]]: ...

    def list_completed(
        self, job_name: str, target_date: date
    ) -> list[dict[str, Any]]: ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def resolve_target_date(raw: str | None, *, today: date | None = None) -> date:
    if raw is None or str(raw).strip() == "":
        current = today or _utcnow().date()
        return current - timedelta(days=1)
    text = str(raw).strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise InvalidTargetDateError(
            f"TARGET_DATE must be YYYY-MM-DD, got {text!r}"
        ) from exc


def sanitize_error(exc: BaseException | str) -> str:
    if isinstance(exc, BaseException):
        text = f"{type(exc).__name__}: {exc}"
    else:
        text = str(exc)
    text = SECRET_RE.sub("[redacted]", text)
    text = text.replace("\n", " ").strip()
    if len(text) > ERROR_MAX:
        text = text[: ERROR_MAX - 3] + "..."
    return text or "Error"


def _supabase_reporting() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        raise RuntimeError("missing SUPABASE_URL or service role key")
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Profile": "reporting",
        "Content-Profile": "reporting",
        "Prefer": "return=representation",
    }


def is_unique_conflict(response: httpx.Response) -> bool:
    if response.status_code == 409:
        return True
    try:
        body = response.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        return False
    code = str(body.get("code") or "")
    message = str(body.get("message") or body.get("hint") or "").lower()
    return code == "23505" or "unique" in message or "duplicate" in message


class SupabaseJobStore:
    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        url, headers = _supabase_reporting()
        response = httpx.post(
            f"{url}/rest/v1/job_runs",
            headers=headers,
            json=row,
            timeout=20.0,
        )
        if is_unique_conflict(response):
            raise JobOverlapError("nightly_export unique conflict on insert")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return payload[0]
        if isinstance(payload, dict):
            return payload
        raise RuntimeError("job_runs insert returned no row")

    def update(self, run_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        url, headers = _supabase_reporting()
        params = {"id": f"eq.{run_id}"}
        expected = fields.pop("_expected_status", None)
        if expected:
            params["status"] = f"eq.{expected}"
        response = httpx.patch(
            f"{url}/rest/v1/job_runs",
            headers=headers,
            params=params,
            json=fields,
            timeout=20.0,
        )
        if is_unique_conflict(response):
            raise JobOverlapError("nightly_export unique conflict on update")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return payload[0]
        raise JobStateError(f"job_runs update matched no row id={run_id}")

    def list_processing(self, job_name: str) -> list[dict[str, Any]]:
        url, headers = _supabase_reporting()
        response = httpx.get(
            f"{url}/rest/v1/job_runs",
            headers=headers,
            params=[
                ("job_name", f"eq.{job_name}"),
                ("status", f"eq.{PROCESSING}"),
                ("select", "id,job_name,target_date,status"),
                ("limit", "1"),
            ],
            timeout=20.0,
        )
        response.raise_for_status()
        rows = response.json()
        return rows if isinstance(rows, list) else []

    def list_completed(
        self, job_name: str, target_date: date
    ) -> list[dict[str, Any]]:
        url, headers = _supabase_reporting()
        response = httpx.get(
            f"{url}/rest/v1/job_runs",
            headers=headers,
            params=[
                ("job_name", f"eq.{job_name}"),
                ("target_date", f"eq.{target_date.isoformat()}"),
                ("status", f"eq.{COMPLETED}"),
                ("select", "id,job_name,target_date,status"),
                ("limit", "1"),
            ],
            timeout=20.0,
        )
        response.raise_for_status()
        rows = response.json()
        return rows if isinstance(rows, list) else []


class MemoryJobStore:
    """In-process store that enforces the partial unique indexes."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def _get(self, run_id: str) -> dict[str, Any]:
        for row in self.rows:
            if str(row.get("id")) == str(run_id):
                return row
        raise JobStateError(f"unknown job run {run_id}")

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        stored = {
            "id": str(row.get("id") or uuid4()),
            "job_name": row["job_name"],
            "target_date": row["target_date"],
            "status": row.get("status", PENDING),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "error_message": row.get("error_message"),
            "created_at": row.get("created_at") or iso_utc(_utcnow()),
        }
        self._assert_indexes(stored, ignore_id=None)
        self.rows.append(stored)
        return dict(stored)

    def update(self, run_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = self._get(run_id)
        expected = fields.pop("_expected_status", None)
        if expected and row.get("status") != expected:
            raise JobStateError(
                f"job run {run_id} status {row.get('status')} != {expected}"
            )
        merged = dict(row)
        merged.update(fields)
        if row.get("status") in TERMINAL and merged.get("status") == PROCESSING:
            raise JobStateError("terminal job cannot return to processing")
        self._assert_indexes(merged, ignore_id=str(run_id))
        row.clear()
        row.update(merged)
        return dict(row)

    def list_processing(self, job_name: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.rows
            if row.get("job_name") == job_name and row.get("status") == PROCESSING
        ]

    def list_completed(
        self, job_name: str, target_date: date
    ) -> list[dict[str, Any]]:
        key = target_date.isoformat()
        return [
            dict(row)
            for row in self.rows
            if row.get("job_name") == job_name
            and str(row.get("target_date"))[:10] == key
            and row.get("status") == COMPLETED
        ]

    def _assert_indexes(self, candidate: dict[str, Any], ignore_id: str | None) -> None:
        name = candidate.get("job_name")
        if candidate.get("status") == PROCESSING:
            for row in self.rows:
                if ignore_id and str(row.get("id")) == ignore_id:
                    continue
                if row.get("job_name") == name and row.get("status") == PROCESSING:
                    raise JobOverlapError("processing lock held")
        if candidate.get("status") == COMPLETED:
            key = str(candidate.get("target_date"))[:10]
            for row in self.rows:
                if ignore_id and str(row.get("id")) == ignore_id:
                    continue
                if (
                    row.get("job_name") == name
                    and str(row.get("target_date"))[:10] == key
                    and row.get("status") == COMPLETED
                ):
                    raise JobOverlapError("completed unique conflict")


_store: JobStore = SupabaseJobStore()


def set_job_store(store: JobStore | None) -> None:
    global _store
    _store = store or SupabaseJobStore()


def reset_job_store() -> None:
    set_job_store(None)


def create_job_run(job_name: str, target_date: date) -> dict[str, Any]:
    return _store.insert(
        {
            "job_name": job_name,
            "target_date": target_date.isoformat(),
            "status": PENDING,
            "started_at": None,
            "finished_at": None,
            "error_message": None,
            "created_at": iso_utc(_utcnow()),
        }
    )


def mark_processing(run_id: str, started_at: datetime | None = None) -> dict[str, Any]:
    started = started_at or _utcnow()
    try:
        return _store.update(
            run_id,
            {
                "status": PROCESSING,
                "started_at": iso_utc(started),
                "_expected_status": PENDING,
            },
        )
    except JobOverlapError:
        try:
            mark_failed(run_id, _utcnow(), "overlap: nightly_export already processing")
        except Exception:
            logger.exception("failed to resolve pending job_run after overlap")
        raise


def mark_completed(run_id: str, finished_at: datetime | None = None) -> dict[str, Any]:
    finished = finished_at or _utcnow()
    return _store.update(
        run_id,
        {
            "status": COMPLETED,
            "finished_at": iso_utc(finished),
            "error_message": None,
            "_expected_status": PROCESSING,
        },
    )


def mark_failed(
    run_id: str,
    finished_at: datetime | None = None,
    error_message: BaseException | str = "failed",
) -> dict[str, Any]:
    finished = finished_at or _utcnow()
    return _store.update(
        run_id,
        {
            "status": FAILED,
            "finished_at": iso_utc(finished),
            "error_message": sanitize_error(error_message),
        },
    )


def has_processing_lock(job_name: str) -> bool:
    return bool(_store.list_processing(job_name))


def has_completed_for_date(job_name: str, target_date: date) -> bool:
    return bool(_store.list_completed(job_name, target_date))
