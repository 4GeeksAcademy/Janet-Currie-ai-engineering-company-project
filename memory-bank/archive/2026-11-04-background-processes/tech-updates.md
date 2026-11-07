# Tech updates — Background processes

- CLI [`scripts/nightly_export.py`](../../../scripts/nightly_export.py) re-execs `services/api/.venv`. Optional `TARGET_DATE=YYYY-MM-DD`; default is yesterday UTC.
- Status machine: [`services/api/app/jobs/job_runner.py`](../../../services/api/app/jobs/job_runner.py). Injectable store for pytest; live path is PostgREST `reporting.job_runs`.
- DDL: [`docs/pipelines/job_runs.sql`](../../../docs/pipelines/job_runs.sql). Partial unique indexes for one `processing` row per job name and one `completed` row per `(job_name, target_date)`.
- CSV: `data/raw/telemetry_YYYY-MM-DD.csv` (gitignored). Atomic temp-file write; existing finals are reused on retry.
- Child pipeline: `[sys.executable, data/pipelines/pipeline.py]`, no shell, no date flag, 900s timeout.
- Tests: `services/api/tests/test_job_runner.py`, `test_nightly_export.py`. Pytest helpers pop `SUPABASE_*` after `app.database` dotenv so unit tests do not hit live PostgREST.
- Live apply of `job_runs.sql`, two-OS-process unique-index proof, and crontab install were not done.
- Durable notes: [`implementation-memory/nightly-export.md`](../../implementation-memory/nightly-export.md).
