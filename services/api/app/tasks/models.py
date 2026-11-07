"""SQLModel table for exhausted Celery failures."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeadLetterTask(SQLModel, table=True):
    __tablename__ = "dead_letter_tasks"

    id: int | None = Field(default=None, primary_key=True)
    task_id: str = Field(unique=True, index=True, max_length=255)
    task_name: str
    attempt_number: int
    error_message: str
    failed_at: datetime = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)
