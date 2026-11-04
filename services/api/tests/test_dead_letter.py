"""Durable dead-letter upsert on the inventory SQLModel engine."""

from __future__ import annotations

import pytest

from app.tasks.models import DeadLetterTask
from app.tasks.store import (
    MemoryDeadLetterStore,
    SqlModelDeadLetterStore,
    record_exhausted_failure,
    set_store,
)
from tests.helpers import reset_inventory_db

TASK_ID = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"


def test_sqlmodel_upsert_is_idempotent() -> None:
    reset_inventory_db()
    store = SqlModelDeadLetterStore()
    first = store.upsert_exhausted(
        task_id=TASK_ID,
        task_name="app.tasks.pipeline_run.run_clinic_supply_pipeline",
        attempt_number=4,
        error_message="httpx.ConnectError: down",
    )
    second = store.upsert_exhausted(
        task_id=TASK_ID,
        task_name="app.tasks.pipeline_run.run_clinic_supply_pipeline",
        attempt_number=4,
        error_message="httpx.ConnectError: down again",
    )
    assert first.task_id == second.task_id == TASK_ID
    found = store.get_by_task_id(TASK_ID)
    assert found is not None
    assert found.error_message.endswith("down again")
    assert "Traceback" not in found.error_message


def test_sanitize_strips_secrets_and_bounds() -> None:
    reset_inventory_db()
    store = SqlModelDeadLetterStore()
    row = store.upsert_exhausted(
        task_id=TASK_ID,
        task_name="app.tasks.pipeline_run.run_clinic_supply_pipeline",
        attempt_number=4,
        error_message="token=supersecret postgresql://user:pass@host/db\n" + ("x" * 500),
    )
    assert "supersecret" not in row.error_message
    assert "postgresql://" not in row.error_message
    assert len(row.error_message) <= 400


def test_memory_store_no_row_until_exhaustion() -> None:
    store = MemoryDeadLetterStore()
    assert store.get_by_task_id(TASK_ID) is None
    store.upsert_exhausted(
        task_id=TASK_ID,
        task_name="app.tasks.pipeline_run.run_clinic_supply_pipeline",
        attempt_number=4,
        error_message="failed",
    )
    assert store.get_by_task_id(TASK_ID) is not None


def test_persistence_failure_is_raised_and_logged() -> None:
    store = MemoryDeadLetterStore()
    store.fail_next = True
    set_store(store)
    with pytest.raises(RuntimeError, match="forced DLQ"):
        record_exhausted_failure(
            task_id=TASK_ID,
            task_name="app.tasks.pipeline_run.run_clinic_supply_pipeline",
            attempt_number=4,
            error_message="failed",
        )


def test_create_all_includes_dead_letter_table() -> None:
    reset_inventory_db()
    from sqlmodel import Session, select

    from app.database import get_engine

    with Session(get_engine()) as session:
        rows = session.exec(select(DeadLetterTask)).all()
    assert rows == []
