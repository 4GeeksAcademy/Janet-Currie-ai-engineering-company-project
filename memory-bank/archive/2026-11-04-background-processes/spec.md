# Spec — Background processes (archived snapshot)

## Requirements

- Independent OS process backs up the previous UTC day's `telemetry_events` to CSV.
- Subprocess-invokes existing `data/pipelines/pipeline.py` (no date flag).
- Records orchestration in `reporting.job_runs`.
- Not scheduled inside FastAPI. Crontab example is documentation only.

## Acceptance criteria

- [x] `scripts/nightly_export.py` and `app.jobs.job_runner`.
- [x] `docs/pipelines/job_runs.sql` with processing/completed partial unique indexes.
- [x] Focused pytest; crontab example not installed.
- [x] Phase guide moved to this archive.

## Interfaces

CLI: `./services/api/.venv/bin/python scripts/nightly_export.py` with optional `TARGET_DATE=YYYY-MM-DD`. Exit 0 on success, duplicate skip, or overlap; non-zero on invalid date or failed eligible run.
