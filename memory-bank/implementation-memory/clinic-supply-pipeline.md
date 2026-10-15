# Clinic supply performance pipeline (Sprint 2)

## Purpose

Turn supply-chain telemetry into one monthly row per clinic for the board-ready Monthly Clinic Supply Performance Report.

## Final Behavior

- ETL in `data/pipelines/pipeline.py`: extract `inbound_order_created`, `outbound_order_created`, `stock_threshold_triggered`, `supply_expiry_flagged`; quarantine invalid rows; aggregate by `clinic_id` + calendar month.
- Cost is `unit_cost × quantity`. Consumption is event count, not quantity sum. Currency from `country` only (no FX).
- Clinic ids are `"1"`–`"12"`.
- API/CLI/tests run `execute_monthly_clinic_supply_performance` (task `.fn()`), not the Prefect `@flow` wrapper, so HTTP POSTs do not start an ephemeral Prefect server.
- JWT routes: `GET /reporting/clinic-months`, `GET /reporting/pipeline-runs`, `POST /reporting/pipeline-runs`. Concurrent POST returns 409.
- CLI: `python3 data/pipelines/pipeline.py` re-execs `services/api/.venv` when prefect is missing.

## Architecture and Data Flow

Telemetry events (PostgREST `telemetry_events`) → extract → transform → load `reporting.clinic_month_kpis` + `reporting.pipeline_runs`. FastAPI `app/reporting` reads those tables. Warehouse DDL is `docs/pipelines/reporting.sql` (not auto-applied).

## Important Files

- `data/pipelines/pipeline.py`
- `docs/pipelines/reporting.sql`
- `services/api/app/reporting/`
- `services/api/app/routers/reporting.py`
- `services/api/tests/test_clinic_supply_pipeline.py`
- `services/api/tests/test_reporting.py`

## Decisions and Constraints

- Prefect `>=3` via `uv` in `services/api`.
- Injectable extract/load/run-log for pytest fakes; no live warehouse in tests.
- Do not change `GET /telemetry/report` or `app/telemetry/analysis.py`.
- No dashboard or subflows until Sprint 3.
- No production Supabase apply; no PHI.

## Validation

Focused pytest 18 passed; full `uv run pytest` 138 passed (after CLI bootstrap); CLI completed with `events_extracted=0` when `SUPABASE_URL` is unset. Live `reporting` schema not applied.
