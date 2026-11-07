# Nightly telemetry export (DEV-53)

Independent OS process. It is **not** started by FastAPI. CSV files are **backups**; the clinic-supply pipeline still reads `telemetry_events`.

## Schedule

Documented default (not installed):

- Expression: `0 2 * * *`
- Timezone: UTC (`02:00 UTC`)
- Example file: [`nightly_export.cron`](nightly_export.cron)

Do not install this crontab or change production hosts unless explicitly authorized.

## Command

From a login/cron environment that is **not** an interactive shell `PATH`:

```bash
cd /ABS/REPO/ROOT
/ABS/REPO/ROOT/services/api/.venv/bin/python /ABS/REPO/ROOT/scripts/nightly_export.py
```

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_KEY`) are loaded from `services/api/.env`. Do not log those values.

Working directory for the child pipeline is the repository root. The child command is `sys.executable data/pipelines/pipeline.py` with no date flag. The pipeline window remains the previous UTC month plus a 7-day lookback.

## Manual run

```bash
TARGET_DATE=2026-10-20 /ABS/REPO/ROOT/services/api/.venv/bin/python /ABS/REPO/ROOT/scripts/nightly_export.py
```

`TARGET_DATE` must be `YYYY-MM-DD`. When unset, the job uses yesterday in UTC.

## Artifacts

| Path | Role |
|------|------|
| `data/raw/telemetry_YYYY-MM-DD.csv` | UTC-day backup of `telemetry_events` |
| `data/raw/nightly_export.log` | Suggested cron log (gitignored if you use this name) |
| `reporting.job_runs` | Orchestration lifecycle |
| `reporting.pipeline_runs` | Pipeline ETL lifecycle (unchanged table) |

CSV files are gitignored. Apply [`job_runs.sql`](job_runs.sql) the same way as [`reporting.sql`](reporting.sql). Grant `USAGE` on schema `reporting` to PostgREST roles if inserts 403.

## Inspect

```sql
select id, job_name, target_date, status, started_at, finished_at, error_message
from reporting.job_runs
order by created_at desc
limit 20;

select run_id, status, window_start, window_end, events_extracted, error
from reporting.pipeline_runs
order by started_at desc
limit 5;
```

Correlate in logs with `job_run_id=` on the nightly process and `run_id` inside the pipeline process. Do not merge the tables.

## Retry a failed date

If `job_runs` is `failed` and `data/raw/telemetry_YYYY-MM-DD.csv` already exists, run the same `TARGET_DATE` again. The job reuses the CSV and invokes the pipeline once more. A `completed` row for that date skips both export and pipeline (exit 0). An overlapping `processing` row also exits 0 without new work.

## Operational limitation

`SIGKILL`, host loss, or a database outage during the final status PATCH can leave a row in `processing`. There is no second lock and no automatic stale-run recovery in v1.

## PR evidence template

- Trigger: host crontab example, not a Compose worker, because infra-40 is two services.
- Cron: `0 2 * * *` UTC.
- Sample successful log (redact secrets).
- Sample failed or overlap-blocked log.
- CSV filename plus a safe first-rows excerpt.
- Migration command: apply `docs/pipelines/job_runs.sql` (record whether live apply was authorized).
- CSV is a backup; pipeline reads the database.
