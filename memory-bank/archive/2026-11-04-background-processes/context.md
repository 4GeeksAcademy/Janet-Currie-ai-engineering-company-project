# Context — HealthCore Digital (archived snapshot)

## Goal

DEV-53 nightly telemetry export on branch `background-processes`. Phase guide: [`background-processes-context.md`](background-processes-context.md). Durable notes: [`implementation-memory/nightly-export.md`](../../implementation-memory/nightly-export.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../../../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), and FastAPI (8000).

## Constraints

- APIs live only under `services/`.
- Nightly job is an OS process, not FastAPI lifespan/APScheduler.
- `job_runs` stays distinct from `pipeline_runs`.
- CSV is a backup; the pipeline still reads `telemetry_events`.
- Do not install crontab or apply warehouse DDL unless asked.

## Relevant files

| Path | Role |
|------|------|
| `background-processes-context.md` | DEV-53 phase guide (this archive) |
| `docs/pipelines/nightly-export-implementation-plan.md` | Execution plan |
| `scripts/nightly_export.py` | Nightly CLI |
| `services/api/app/jobs/job_runner.py` | Status machine |
| `docs/pipelines/job_runs.sql` | `reporting.job_runs` DDL |
