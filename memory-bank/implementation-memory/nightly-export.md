# Nightly telemetry export (DEV-53)

## Purpose

Back up one UTC day's telemetry to CSV and trigger the existing clinic-supply pipeline without embedding a scheduler in FastAPI.

## Final Behavior

- CLI `scripts/nightly_export.py` uses yesterday UTC unless `TARGET_DATE=YYYY-MM-DD`.
- Writes `data/raw/telemetry_YYYY-MM-DD.csv` only when that final file is absent (atomic temp + rename).
- Invokes `data/pipelines/pipeline.py` once per eligible run via `sys.executable` (no date flag; pipeline keeps its monthly window).
- Records orchestration in `reporting.job_runs` (`pending → processing → completed|failed`).
- Exit 0 on success, duplicate skip, or overlap; non-zero on invalid date or failed eligible run.

## Architecture and Data Flow

Host crontab example → `scripts/nightly_export.py` → `app.jobs.job_runner` → `reporting.job_runs`. CSV export reads `public.telemetry_events`. Child process runs the existing ETL, which still writes `reporting.pipeline_runs` and KPI rows.

## Important Files

- `memory-bank/archive/2026-11-04-background-processes/background-processes-context.md`
- `scripts/nightly_export.py`
- `services/api/app/jobs/job_runner.py`
- `docs/pipelines/job_runs.sql`
- `docs/pipelines/nightly-export.md`
- `docs/pipelines/nightly_export.cron`
- `services/api/tests/test_job_runner.py`
- `services/api/tests/test_nightly_export.py`

## Decisions and Constraints

- `job_runs` is PostgREST `reporting`, not inventory SQLModel.
- Processing-row partial unique index is the distributed lock.
- CSV is a backup, not pipeline input.
- Do not install crontab or apply SQL live unless asked.
- Do not import `app.jobs` from FastAPI `main.py`.

## Validation

Focused job + telemetry/pipeline/reporting pytest **48 passed**. Full `uv run pytest` **165 passed**. Invalid `TARGET_DATE` CLI exits `2`. Live `job_runs.sql` apply, two-process unique-index race, and crontab install remain unverified.

## Maintenance Notes

`SIGKILL` or a DB outage during the final status PATCH can leave a row in `processing`. Stale-run recovery was out of scope for v1.
