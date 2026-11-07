"""job_runs state machine, dates, and fake unique-index lock."""

from __future__ import annotations

from datetime import date, datetime, timezone

import httpx
import pytest

from app.jobs import job_runner as jobs


@pytest.fixture
def store() -> jobs.MemoryJobStore:
    memory = jobs.MemoryJobStore()
    jobs.set_job_store(memory)
    yield memory
    jobs.reset_job_store()


def test_default_target_is_yesterday_utc() -> None:
    assert jobs.resolve_target_date(None, today=date(2026, 10, 21)) == date(2026, 10, 20)


def test_valid_target_date_is_accepted() -> None:
    assert jobs.resolve_target_date("2026-01-02") == date(2026, 1, 2)


def test_blank_target_date_is_treated_as_absent() -> None:
    assert jobs.resolve_target_date("  ", today=date(2026, 10, 21)) == date(2026, 10, 20)


@pytest.mark.parametrize("raw", ["21-10-2026", "2026-13-01", "not-a-date", "2026-02-30"])
def test_malformed_and_impossible_dates_fail(raw: str) -> None:
    with pytest.raises(jobs.InvalidTargetDateError):
        jobs.resolve_target_date(raw)


def test_month_end_year_end_and_leap_day() -> None:
    assert jobs.resolve_target_date(None, today=date(2024, 3, 1)) == date(2024, 2, 29)
    assert jobs.resolve_target_date(None, today=date(2025, 3, 1)) == date(2025, 2, 28)
    assert jobs.resolve_target_date(None, today=date(2026, 1, 1)) == date(2025, 12, 31)
    assert jobs.resolve_target_date(None, today=date(2026, 5, 1)) == date(2026, 4, 30)


def test_pending_processing_completed_timestamps(store: jobs.MemoryJobStore) -> None:
    started = datetime(2026, 10, 21, 2, 0, tzinfo=timezone.utc)
    finished = datetime(2026, 10, 21, 2, 5, tzinfo=timezone.utc)
    row = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 20))
    assert row["status"] == jobs.PENDING
    assert row["started_at"] is None
    processing = jobs.mark_processing(row["id"], started)
    assert processing["status"] == jobs.PROCESSING
    assert processing["started_at"].startswith("2026-10-21T02:00:00")
    done = jobs.mark_completed(row["id"], finished)
    assert done["status"] == jobs.COMPLETED
    assert done["finished_at"].startswith("2026-10-21T02:05:00")
    assert done["error_message"] is None


def test_failure_records_safe_error_and_finished_at(store: jobs.MemoryJobStore) -> None:
    row = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 20))
    jobs.mark_processing(row["id"])
    failed = jobs.mark_failed(
        row["id"],
        datetime(2026, 10, 21, 3, 0, tzinfo=timezone.utc),
        RuntimeError("postgresql://user:secret@host/db boom"),
    )
    assert failed["status"] == jobs.FAILED
    assert failed["finished_at"].startswith("2026-10-21T03:00:00")
    assert "secret" not in failed["error_message"].lower()
    assert "[redacted]" in failed["error_message"]
    assert failed["error_message"].startswith("RuntimeError:")


def test_terminal_cannot_return_to_processing(store: jobs.MemoryJobStore) -> None:
    row = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 20))
    jobs.mark_processing(row["id"])
    jobs.mark_completed(row["id"])
    with pytest.raises(jobs.JobStateError):
        jobs.mark_processing(row["id"])


def test_completed_lookup_is_scoped_by_job_and_date(store: jobs.MemoryJobStore) -> None:
    first = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 20))
    jobs.mark_processing(first["id"])
    jobs.mark_completed(first["id"])
    other = jobs.create_job_run("other_job", date(2026, 10, 20))
    jobs.mark_processing(other["id"])
    jobs.mark_completed(other["id"])
    assert jobs.has_completed_for_date(jobs.JOB_NAME, date(2026, 10, 20)) is True
    assert jobs.has_completed_for_date(jobs.JOB_NAME, date(2026, 10, 19)) is False


def test_processing_lookup_is_global_to_job_name(store: jobs.MemoryJobStore) -> None:
    row = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 19))
    jobs.mark_processing(row["id"])
    assert jobs.has_processing_lock(jobs.JOB_NAME) is True
    assert jobs.has_processing_lock("other_job") is False


def test_second_processing_raises_overlap_and_fails_pending(
    store: jobs.MemoryJobStore,
) -> None:
    first = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 18))
    jobs.mark_processing(first["id"])
    second = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 19))
    with pytest.raises(jobs.JobOverlapError):
        jobs.mark_processing(second["id"])
    zombie = store._get(second["id"])
    assert zombie["status"] == jobs.FAILED
    assert "overlap" in zombie["error_message"]


def test_failed_history_can_be_retried(store: jobs.MemoryJobStore) -> None:
    first = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 20))
    jobs.mark_processing(first["id"])
    jobs.mark_failed(first["id"], error_message="boom")
    assert jobs.has_completed_for_date(jobs.JOB_NAME, date(2026, 10, 20)) is False
    retry = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 20))
    jobs.mark_processing(retry["id"])
    jobs.mark_completed(retry["id"])
    assert jobs.has_completed_for_date(jobs.JOB_NAME, date(2026, 10, 20)) is True


def test_unique_conflict_mapper() -> None:
    conflict = httpx.Response(409, json={"code": "23505", "message": "duplicate key"})
    other = httpx.Response(400, json={"code": "23505", "message": "duplicate key value"})
    ok = httpx.Response(200, json=[])
    assert jobs.is_unique_conflict(conflict) is True
    assert jobs.is_unique_conflict(other) is True
    assert jobs.is_unique_conflict(ok) is False
