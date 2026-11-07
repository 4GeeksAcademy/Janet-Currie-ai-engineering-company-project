"""Injectable dead-letter persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_engine
from app.jobs.job_runner import sanitize_error
from app.tasks.models import DeadLetterTask

logger = logging.getLogger(__name__)

TASK_NAME_PIPELINE = "app.tasks.pipeline_run.run_clinic_supply_pipeline"


class DeadLetterStore(Protocol):
    def upsert_exhausted(
        self,
        *,
        task_id: str,
        task_name: str,
        attempt_number: int,
        error_message: str,
    ) -> DeadLetterTask: ...

    def get_by_task_id(self, task_id: str) -> DeadLetterTask | None: ...


class MemoryDeadLetterStore:
    def __init__(self) -> None:
        self.rows: dict[str, DeadLetterTask] = {}
        self.fail_next = False

    def upsert_exhausted(
        self,
        *,
        task_id: str,
        task_name: str,
        attempt_number: int,
        error_message: str,
    ) -> DeadLetterTask:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("forced DLQ persistence failure")
        now = datetime.now(timezone.utc)
        existing = self.rows.get(task_id)
        if existing is not None:
            existing.attempt_number = attempt_number
            existing.error_message = sanitize_error(error_message)
            existing.failed_at = now
            return existing
        row = DeadLetterTask(
            id=len(self.rows) + 1,
            task_id=task_id,
            task_name=task_name,
            attempt_number=attempt_number,
            error_message=sanitize_error(error_message),
            failed_at=now,
            created_at=now,
        )
        self.rows[task_id] = row
        return row

    def get_by_task_id(self, task_id: str) -> DeadLetterTask | None:
        return self.rows.get(task_id)


class SqlModelDeadLetterStore:
    def upsert_exhausted(
        self,
        *,
        task_id: str,
        task_name: str,
        attempt_number: int,
        error_message: str,
    ) -> DeadLetterTask:
        safe = sanitize_error(error_message)
        now = datetime.now(timezone.utc)
        with Session(get_engine()) as session:
            existing = session.exec(
                select(DeadLetterTask).where(DeadLetterTask.task_id == task_id)
            ).first()
            if existing is not None:
                existing.attempt_number = attempt_number
                existing.error_message = safe
                existing.failed_at = now
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            row = DeadLetterTask(
                task_id=task_id,
                task_name=task_name,
                attempt_number=attempt_number,
                error_message=safe,
                failed_at=now,
                created_at=now,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.exec(
                    select(DeadLetterTask).where(DeadLetterTask.task_id == task_id)
                ).first()
                if existing is None:
                    raise
                existing.attempt_number = attempt_number
                existing.error_message = safe
                existing.failed_at = now
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            session.refresh(row)
            return row

    def get_by_task_id(self, task_id: str) -> DeadLetterTask | None:
        with Session(get_engine()) as session:
            return session.exec(
                select(DeadLetterTask).where(DeadLetterTask.task_id == task_id)
            ).first()


_store: DeadLetterStore | None = None


def get_store() -> DeadLetterStore:
    return _store if _store is not None else SqlModelDeadLetterStore()


def set_store(store: DeadLetterStore | None) -> None:
    global _store
    _store = store


def reset_store() -> None:
    set_store(None)


def record_exhausted_failure(
    *,
    task_id: str,
    task_name: str,
    attempt_number: int,
    error_message: str,
) -> DeadLetterTask:
    try:
        return get_store().upsert_exhausted(
            task_id=task_id,
            task_name=task_name,
            attempt_number=attempt_number,
            error_message=error_message,
        )
    except Exception:
        logger.critical(
            "DLQ persistence failed task_id=%s task_name=%s attempt_number=%s",
            task_id,
            task_name,
            attempt_number,
        )
        raise
