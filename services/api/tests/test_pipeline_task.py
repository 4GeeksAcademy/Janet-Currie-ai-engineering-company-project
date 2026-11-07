"""Clinic-supply Celery task: execute once, retry backoff, DLQ on exhaustion."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

import httpx
import pytest
from celery.exceptions import Retry

from app.tasks.pipeline_run import (
    PermanentTaskError,
    retry_countdown,
    run_clinic_supply_pipeline,
    set_execute,
)
from app.tasks.store import MemoryDeadLetterStore, set_store
from pipelines.pipeline import PipelineBusyError

TASK_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@contextmanager
def task_request(*, retries: int = 0, task_id: str = TASK_ID) -> Iterator[None]:
    run_clinic_supply_pipeline.push_request(id=task_id, retries=retries)
    try:
        yield
    finally:
        run_clinic_supply_pipeline.pop_request()


def _ok(_month: date | None) -> dict:
    return {
        "run_id": "run-1",
        "status": "completed",
        "records_processed": 2,
        "events_extracted": 2,
        "events_quarantined": 0,
    }


def test_retry_countdown_increases() -> None:
    assert retry_countdown(0) == 5
    assert retry_countdown(1) == 10
    assert retry_countdown(2) == 20
    assert retry_countdown(8) == 60


def test_success_calls_execute_once() -> None:
    calls: list[date | None] = []

    def execute(month: date | None) -> dict:
        calls.append(month)
        return _ok(month)

    set_execute(execute)
    store = MemoryDeadLetterStore()
    set_store(store)
    with task_request(retries=0):
        result = run_clinic_supply_pipeline.run("2026-07-01")
    assert calls == [date(2026, 7, 1)]
    assert result["run_id"] == "run-1"
    assert result["month_start"] == "2026-07-01"
    assert store.rows == {}


def _patch_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_retry(exc=None, countdown=None, **_kwargs):
        raise Retry(exc=exc, when=countdown)

    monkeypatch.setattr(run_clinic_supply_pipeline, "retry", fake_retry)


def test_transient_failure_retries_same_task_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_retry(monkeypatch)
    store = MemoryDeadLetterStore()
    set_execute(lambda _m: (_ for _ in ()).throw(httpx.ConnectError("down")))
    set_store(store)
    with task_request(retries=0):
        with pytest.raises(Retry) as caught:
            run_clinic_supply_pipeline.run("2026-07-01")
    assert caught.value.when == 5
    assert store.get_by_task_id(TASK_ID) is None


def test_second_retry_uses_longer_countdown(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_retry(monkeypatch)
    set_execute(lambda _m: (_ for _ in ()).throw(httpx.ConnectError("down")))
    set_store(MemoryDeadLetterStore())
    with task_request(retries=1):
        with pytest.raises(Retry) as caught:
            run_clinic_supply_pipeline.run("2026-07-01")
    assert caught.value.when == 10


def test_busy_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_retry(monkeypatch)
    set_execute(lambda _m: (_ for _ in ()).throw(PipelineBusyError()))
    set_store(MemoryDeadLetterStore())
    with task_request(retries=0):
        with pytest.raises(Retry):
            run_clinic_supply_pipeline.run("2026-07-01")


def test_permanent_month_skips_retry_and_writes_dlq() -> None:
    store = MemoryDeadLetterStore()
    set_store(store)
    set_execute(_ok)
    with task_request(retries=0):
        with pytest.raises(PermanentTaskError):
            run_clinic_supply_pipeline.run("2026-07-15")
    row = store.get_by_task_id(TASK_ID)
    assert row is not None
    assert row.attempt_number == 1
    assert "month_start" in row.error_message


def test_exhaustion_writes_one_dlq_row() -> None:
    store = MemoryDeadLetterStore()
    set_store(store)
    set_execute(lambda _m: (_ for _ in ()).throw(httpx.ConnectError("down")))
    with task_request(retries=3):
        with pytest.raises(httpx.ConnectError):
            run_clinic_supply_pipeline.run("2026-07-01")
    row = store.get_by_task_id(TASK_ID)
    assert row is not None
    assert row.attempt_number == 4
    assert row.task_name == "app.tasks.pipeline_run.run_clinic_supply_pipeline"
    assert "ConnectError" in row.error_message
    assert store.upsert_exhausted(
        task_id=TASK_ID,
        task_name=row.task_name,
        attempt_number=4,
        error_message="again",
    )
    assert len(store.rows) == 1
