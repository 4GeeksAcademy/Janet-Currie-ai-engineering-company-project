# Tech updates — Data pipeline

- Prefect 3 in `services/api` (`prefect>=3`). Main flow coordinates extract/transform/load subflows; optional heartbeat uses `return_state=True`.
- Production runner is `execute_monthly_clinic_supply_performance` (task `.fn()`). CLI `python3 data/pipelines/pipeline.py` re-execs `services/api/.venv`.
- Destination: `reporting.monthly_clinic_supply_performance` + `reporting.pipeline_runs`. DDL: [`docs/pipelines/reporting.sql`](../../../docs/pipelines/reporting.sql). Live apply also needed `GRANT USAGE` on schema `reporting` for PostgREST roles.
- JWT reporting on existing FastAPI app. Dashboard: `uis/web` `/backoffice/reporting/monthly-clinic-supply-performance`.
- Isolated tests: `tests/pipelines/test_pipeline.py`.
- Durable notes: [`implementation-memory/clinic-supply-pipeline.md`](../../implementation-memory/clinic-supply-pipeline.md).
- Live smoke 2026-10-21: completed run with `events_extracted=0`; dashboard showed that run. No populated US/UK rows (empty `telemetry_events`).
