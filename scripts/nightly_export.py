"""Nightly telemetry CSV backup and pipeline trigger (DEV-53)."""

from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"
VENV_PY = API_ROOT / ".venv" / "bin" / "python"
PIPELINE_SCRIPT = REPO_ROOT / "data" / "pipelines" / "pipeline.py"
RAW_DIR = REPO_ROOT / "data" / "raw"
JOB_NAME = "nightly_export"
CSV_COLUMNS = [
    "id",
    "timestamp",
    "service",
    "event_type",
    "level",
    "value",
    "message",
    "tags",
]
PIPELINE_TIMEOUT_SECONDS = 900

if __name__ == "__main__":
    if str(API_ROOT) not in sys.path:
        sys.path.insert(0, str(API_ROOT))
    try:
        import httpx  # noqa: F401
        from dotenv import load_dotenv
    except ImportError:
        if VENV_PY.exists() and Path(sys.prefix).resolve() != (API_ROOT / ".venv").resolve():
            os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])
        raise SystemExit("httpx is not installed; run `uv sync` in services/api")
    load_dotenv(API_ROOT / ".env")

from app.jobs.job_runner import (  # noqa: E402
    COMPLETED,
    InvalidTargetDateError,
    JobOverlapError,
    PROCESSING,
    create_job_run,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
    resolve_target_date,
    sanitize_error,
)

logger = logging.getLogger("nightly_export")

FetchEventsFn = Callable[[datetime, datetime], list[dict[str, Any]]]
RunPipelineFn = Callable[[], int]


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        UTCFormatter("%(asctime)s UTC %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%SZ")
    )
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(
    level: int,
    status: str,
    reason: str,
    *,
    target_date: date | None = None,
    job_run_id: str | None = None,
) -> None:
    logger.log(
        level,
        "job_name=%s status=%s target_date=%s job_run_id=%s %s",
        JOB_NAME,
        status,
        target_date.isoformat() if target_date else "-",
        job_run_id or "-",
        reason,
    )


def utc_day_window(target: date) -> tuple[datetime, datetime]:
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def csv_path_for(target: date, *, raw_dir: Path | None = None) -> Path:
    folder = raw_dir or RAW_DIR
    return folder / f"telemetry_{target.isoformat()}.csv"


def _public_supabase() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        raise RuntimeError("missing SUPABASE_URL or service role key")
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def fetch_telemetry_events(window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    import httpx

    url, headers = _public_supabase()
    response = httpx.get(
        f"{url}/rest/v1/telemetry_events",
        headers=headers,
        params=[
            ("timestamp", f"gte.{window_start.isoformat()}"),
            ("timestamp", f"lt.{window_end.isoformat()}"),
            ("select", ",".join(CSV_COLUMNS)),
            ("order", "timestamp.asc,id.asc"),
        ],
        timeout=20.0,
    )
    response.raise_for_status()
    rows = response.json()
    return rows if isinstance(rows, list) else []


def _cell(row: dict[str, Any], column: str) -> str:
    value = row.get(column)
    if column == "tags":
        if value is None:
            value = {}
        return json.dumps(value, sort_keys=True, default=str)
    if value is None:
        return ""
    return str(value)


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid4().hex[:8]}")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({column: _cell(row, column) for column in CSV_COLUMNS})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def export_csv(
    target: date,
    *,
    fetch_events: FetchEventsFn | None = None,
    raw_dir: Path | None = None,
) -> tuple[Path, str]:
    path = csv_path_for(target, raw_dir=raw_dir)
    if path.exists():
        return path, "reused"
    start, end = utc_day_window(target)
    fetcher = fetch_events or fetch_telemetry_events
    rows = fetcher(start, end)
    write_csv_atomic(path, rows)
    return path, "created"


def pipeline_command() -> list[str]:
    return [sys.executable, str(PIPELINE_SCRIPT)]


def run_pipeline_subprocess(*, timeout: int = PIPELINE_TIMEOUT_SECONDS) -> int:
    if not PIPELINE_SCRIPT.exists():
        raise FileNotFoundError(f"pipeline CLI missing: {PIPELINE_SCRIPT}")
    completed = subprocess.run(
        pipeline_command(),
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        check=False,
        timeout=timeout,
        shell=False,
    )
    return int(completed.returncode)


def run_nightly_export(
    *,
    target_date_raw: str | None = None,
    today: date | None = None,
    fetch_events: FetchEventsFn | None = None,
    run_pipeline: RunPipelineFn | None = None,
    raw_dir: Path | None = None,
) -> int:
    try:
        target = resolve_target_date(target_date_raw, today=today)
    except InvalidTargetDateError as exc:
        log_event(logging.ERROR, "failed", sanitize_error(exc))
        return 2

    log_event(logging.INFO, "pending", "start", target_date=target)

    if has_processing_lock(JOB_NAME):
        log_event(
            logging.INFO,
            PROCESSING,
            "overlap blocked",
            target_date=target,
        )
        return 0
    if has_completed_for_date(JOB_NAME, target):
        log_event(
            logging.INFO,
            COMPLETED,
            "duplicate skip",
            target_date=target,
        )
        return 0

    record = create_job_run(JOB_NAME, target)
    run_id = str(record["id"])
    log_event(logging.INFO, "pending", "created", target_date=target, job_run_id=run_id)
    try:
        mark_processing(run_id)
        log_event(
            logging.INFO,
            PROCESSING,
            "processing",
            target_date=target,
            job_run_id=run_id,
        )
        path, csv_action = export_csv(
            target, fetch_events=fetch_events, raw_dir=raw_dir
        )
        log_event(
            logging.INFO,
            PROCESSING,
            f"csv {csv_action} {path.name}",
            target_date=target,
            job_run_id=run_id,
        )
        runner = run_pipeline or run_pipeline_subprocess
        log_event(
            logging.INFO,
            PROCESSING,
            "pipeline start",
            target_date=target,
            job_run_id=run_id,
        )
        code = runner()
        if code != 0:
            raise RuntimeError(f"pipeline exited {code}")
        mark_completed(run_id)
        log_event(
            logging.INFO,
            COMPLETED,
            "completed",
            target_date=target,
            job_run_id=run_id,
        )
        return 0
    except JobOverlapError:
        log_event(
            logging.INFO,
            PROCESSING,
            "overlap blocked",
            target_date=target,
            job_run_id=run_id,
        )
        return 0
    except Exception as exc:
        try:
            mark_failed(run_id, error_message=exc)
        except Exception:
            logger.exception(
                "job_name=%s status=failed target_date=%s job_run_id=%s status-persistence failure",
                JOB_NAME,
                target.isoformat(),
                run_id,
            )
        log_event(
            logging.ERROR,
            "failed",
            sanitize_error(exc),
            target_date=target,
            job_run_id=run_id,
        )
        return 1


def main() -> int:
    configure_logging()
    return run_nightly_export(target_date_raw=os.getenv("TARGET_DATE"))


if __name__ == "__main__":
    raise SystemExit(main())
