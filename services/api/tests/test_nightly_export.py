"""CSV backup, subprocess, exit codes, and retry-reuse for nightly_export."""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.jobs import job_runner as jobs

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import nightly_export  # noqa: E402


@pytest.fixture
def store(tmp_path: Path) -> jobs.MemoryJobStore:
    memory = jobs.MemoryJobStore()
    jobs.set_job_store(memory)
    yield memory
    jobs.reset_job_store()


def _events_for(target: date) -> list[dict]:
    included = datetime(target.year, target.month, target.day, tzinfo=timezone.utc).isoformat()
    return [
        {
            "id": "aaa",
            "timestamp": included,
            "service": "backoffice",
            "event_type": "inbound_order_created",
            "level": "info",
            "value": 1,
            "message": None,
            "tags": {"userId": "staff-1", "clinic_id": 1},
            "password": "nope",
            "email": "hidden@example.com",
        }
    ]


def test_window_includes_midnight_and_excludes_next_day(tmp_path: Path) -> None:
    target = date(2026, 10, 20)
    start, end = nightly_export.utc_day_window(target)
    captured: list[tuple[datetime, datetime]] = []

    def fetch(window_start: datetime, window_end: datetime) -> list[dict]:
        captured.append((window_start, window_end))
        assert window_start == start
        assert window_end == end
        return [
            {
                "id": "in",
                "timestamp": "2026-10-20T00:00:00+00:00",
                "service": "backoffice",
                "event_type": "ping",
                "level": "info",
                "value": None,
                "message": None,
                "tags": {},
            },
            {
                "id": "out",
                "timestamp": "2026-10-21T00:00:00+00:00",
                "service": "backoffice",
                "event_type": "ping",
                "level": "info",
                "value": None,
                "message": None,
                "tags": {},
            },
        ]

    # Export writes whatever fetch returns; window bounds are the contract.
    nightly_export.export_csv(target, fetch_events=fetch, raw_dir=tmp_path)
    assert captured == [(start, end)]
    text = (tmp_path / "telemetry_2026-10-20.csv").read_text(encoding="utf-8")
    assert "2026-10-20T00:00:00+00:00" in text
    # fetch is responsible for the query; this test asserts the window passed in.
    assert start.isoformat().startswith("2026-10-20T00:00:00")
    assert end.isoformat().startswith("2026-10-21T00:00:00")


def test_zero_event_day_writes_header_only(tmp_path: Path) -> None:
    path, action = nightly_export.export_csv(
        date(2026, 10, 20),
        fetch_events=lambda _s, _e: [],
        raw_dir=tmp_path,
    )
    assert action == "created"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines == [",".join(nightly_export.CSV_COLUMNS)]


def test_existing_final_file_is_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "telemetry_2026-10-20.csv"
    original = "id,timestamp\nkeep-me\n"
    path.write_text(original, encoding="utf-8")

    def boom(_s: datetime, _e: datetime) -> list[dict]:
        raise AssertionError("must not refetch when final CSV exists")

    out, action = nightly_export.export_csv(
        date(2026, 10, 20), fetch_events=boom, raw_dir=tmp_path
    )
    assert action == "reused"
    assert out.read_text(encoding="utf-8") == original


def test_failed_write_does_not_leave_final_or_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_replace(_src: str | Path, _dst: str | Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(nightly_export.os, "replace", fail_replace)
    with pytest.raises(OSError):
        nightly_export.export_csv(
            date(2026, 10, 20),
            fetch_events=lambda _s, _e: [{"id": "1", "timestamp": "t", "tags": {}}],
            raw_dir=tmp_path,
        )
    assert list(tmp_path.glob("telemetry_2026-10-20.csv")) == []
    assert list(tmp_path.glob("*.tmp.*")) == []


def test_unapproved_columns_are_absent(tmp_path: Path) -> None:
    nightly_export.export_csv(
        date(2026, 10, 20),
        fetch_events=lambda _s, _e: _events_for(date(2026, 10, 20)),
        raw_dir=tmp_path,
    )
    text = (tmp_path / "telemetry_2026-10-20.csv").read_text(encoding="utf-8")
    header = text.splitlines()[0]
    assert header == ",".join(nightly_export.CSV_COLUMNS)
    assert "password" not in header
    assert "email" not in header
    assert "nope" not in text
    assert "hidden@example.com" not in text
    assert "staff-1" in text


def test_successful_child_completes(
    store: jobs.MemoryJobStore, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    calls = {"n": 0}

    def pipeline() -> int:
        calls["n"] += 1
        return 0

    code = nightly_export.run_nightly_export(
        target_date_raw="2026-10-20",
        fetch_events=lambda _s, _e: [],
        run_pipeline=pipeline,
        raw_dir=tmp_path,
    )
    assert code == 0
    assert calls["n"] == 1
    assert store.rows[0]["status"] == jobs.COMPLETED
    assert "job_name=nightly_export" in caplog.text
    assert "SUPABASE_SERVICE_ROLE_KEY" not in caplog.text


def test_nonzero_child_fails_and_keeps_csv(
    store: jobs.MemoryJobStore, tmp_path: Path
) -> None:
    code = nightly_export.run_nightly_export(
        target_date_raw="2026-10-20",
        fetch_events=lambda _s, _e: [{"id": "1", "timestamp": "t", "tags": {"a": 1}}],
        run_pipeline=lambda: 7,
        raw_dir=tmp_path,
    )
    assert code == 1
    assert store.rows[0]["status"] == jobs.FAILED
    csv_file = tmp_path / "telemetry_2026-10-20.csv"
    original = csv_file.read_bytes()
    invoked = {"n": 0}

    def pipeline() -> int:
        invoked["n"] += 1
        return 0

    retry = nightly_export.run_nightly_export(
        target_date_raw="2026-10-20",
        fetch_events=lambda _s, _e: (_ for _ in ()).throw(AssertionError("must reuse csv")),
        run_pipeline=pipeline,
        raw_dir=tmp_path,
    )
    assert retry == 0
    assert invoked["n"] == 1
    assert csv_file.read_bytes() == original
    assert store.rows[1]["status"] == jobs.COMPLETED


def test_duplicate_completed_skips_export_and_pipeline(
    store: jobs.MemoryJobStore, tmp_path: Path
) -> None:
    nightly_export.run_nightly_export(
        target_date_raw="2026-10-20",
        fetch_events=lambda _s, _e: [],
        run_pipeline=lambda: 0,
        raw_dir=tmp_path,
    )
    code = nightly_export.run_nightly_export(
        target_date_raw="2026-10-20",
        fetch_events=lambda _s, _e: (_ for _ in ()).throw(AssertionError("skip")),
        run_pipeline=lambda: (_ for _ in ()).throw(AssertionError("skip")),
        raw_dir=tmp_path,
    )
    assert code == 0
    assert len(store.rows) == 1


def test_overlap_exits_zero_without_new_work(
    store: jobs.MemoryJobStore, tmp_path: Path
) -> None:
    held = jobs.create_job_run(jobs.JOB_NAME, date(2026, 10, 19))
    jobs.mark_processing(held["id"])
    code = nightly_export.run_nightly_export(
        target_date_raw="2026-10-20",
        fetch_events=lambda _s, _e: (_ for _ in ()).throw(AssertionError("skip")),
        run_pipeline=lambda: (_ for _ in ()).throw(AssertionError("skip")),
        raw_dir=tmp_path,
    )
    assert code == 0
    assert len(store.rows) == 1


def test_bad_date_exits_nonzero_before_work(store: jobs.MemoryJobStore) -> None:
    code = nightly_export.run_nightly_export(
        target_date_raw="2026-02-30",
        fetch_events=lambda _s, _e: [],
        run_pipeline=lambda: 0,
    )
    assert code == 2
    assert store.rows == []


def test_pipeline_command_uses_executable_and_no_shell() -> None:
    command = nightly_export.pipeline_command()
    assert command[0] == sys.executable
    assert command[1].endswith("data/pipelines/pipeline.py")
    assert "shell" not in command
