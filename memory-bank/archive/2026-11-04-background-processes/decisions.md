# Decisions — Background processes (archived snapshot)

Standing nightly-job decisions remain in the active [`decisions.md`](../../decisions.md). Highlights:

- `job_runs` lives in PostgREST `reporting`, not inventory SQLModel.
- Trigger is a version-controlled host crontab example (`0 2 * * *` UTC), not a Compose worker.
- Pipeline CLI is unchanged: `data/pipelines/pipeline.py` with no date flag.
- Distributed lock is a partial unique index on `status = 'processing'`.
- CSV is an audit backup; the pipeline still reads `telemetry_events`.
