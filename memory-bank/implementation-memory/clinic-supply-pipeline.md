# Clinic supply performance pipeline

## Purpose

Turn supply-chain telemetry into one monthly row per clinic for the board-ready Monthly Clinic Supply Performance Report.

## Final Behavior

- ETL in `data/pipelines/pipeline.py`: extract the four supply-chain event types; quarantine invalid rows; aggregate by `clinic_id` + calendar month.
- Cost is `unit_cost × quantity`. Consumption is event count, not quantity sum. Currency from `country` only (no FX). Clinic ids are `"1"`–`"12"`.
- Prefect topology: main flow `monthly_clinic_supply_performance` coordinates `extract_clinic_supply_events_flow`, `transform_clinic_month_kpis_flow`, and `load_monthly_clinic_supply_performance_flow`. Optional heartbeat subflow uses `return_state=True`.
- API/CLI/tests run `execute_monthly_clinic_supply_performance` (`task.fn()`), not `@flow()`, so HTTP POSTs do not start an ephemeral Prefect server.
- JWT routes: `GET /reporting/monthly-clinic-supply-performance`, `GET /reporting/pipeline-runs/latest`, `POST /reporting/pipeline-runs` (409 if running).
- Dashboard: `uis/web` `/backoffice/reporting/monthly-clinic-supply-performance` fetches the KPI endpoint; USD and GBP stay in separate sections.
- CLI: `python3 data/pipelines/pipeline.py` re-execs `services/api/.venv` when prefect is missing.

## Architecture and Data Flow

Telemetry events (PostgREST `telemetry_events`) → extract → transform → load `reporting.monthly_clinic_supply_performance` + `reporting.pipeline_runs`. FastAPI `app/reporting` reads those tables. Staff UI reads the reporting HTTP API only. Warehouse DDL is `docs/pipelines/reporting.sql` (not auto-applied).

## Important Files

- `data/pipelines/pipeline.py`
- `docs/pipelines/reporting.sql`
- `tests/pipelines/test_pipeline.py`
- `services/api/app/reporting/`
- `services/api/app/routers/reporting.py`
- `uis/web/src/lib/reporting.ts`
- `uis/web/src/components/reporting/MonthlyClinicSupplyReport.tsx`

## Decisions and Constraints

- Prefect `>=3` via `uv` in `services/api`.
- Injectable extract/load/run-log for pytest fakes; no live warehouse in tests.
- Do not change `GET /telemetry/report` or `app/telemetry/analysis.py`.
- No production Supabase apply; no PHI; no cross-currency totals.
- Advisory lock not shipped (single API process).

## Validation

Isolated `tests/pipelines/test_pipeline.py` **7 passed**. Focused API pytest **21 passed**. Full `uv run pytest` **138 passed**. Jest reporting **10 passed**. `npm run typecheck -w uis/web` pass. CLI completed with `events_extracted=0` when `SUPABASE_URL` is unset. Live `reporting` schema not applied. Headed dashboard smoke not run (staff UI and API were not listening locally); Jest covered loading/empty/error/populated.
