# Progress — Active iteration

## Current state

On `data-pipeline`. Sprint 3 implemented (subflows, isolated tests, clinic-supply dashboard). Next: wait for the user to push or open a PR. Do not push unless asked.

## Completed (standing)

- Sprint 1 design + inbound `unit_cost`.
- Sprint 2: Prefect ETL + JWT `/reporting` routes.
- Sprint 3: extract/transform/load subflows, `tests/pipelines/test_pipeline.py`, `uis/web` dashboard.

## Validation results

- Isolated pytest `tests/pipelines/test_pipeline.py`: **7 passed**.
- Focused API pytest (pipeline + reporting + serialization + telemetry report): **21 passed**.
- Full `uv run pytest` in `services/api`: **138 passed**.
- Jest reporting suite: **10 passed**.
- `npm run typecheck -w uis/web`: pass.
- Live CLI (2026-10-21): credentials matched; granted `USAGE` on schema `reporting`; run **completed** `events_extracted=0` / `records_processed=0` (empty `telemetry_events` in Sep window). `pipeline_runs` row persisted (`b0a933e5-…`).
- Headed dashboard: empty KPI copy plus “Latest run completed: 0 clinic-month rows, 0 events extracted”. Populated US/UK not shown (no source events).

## Blockers

None.

## Next steps

1. Do not push or open a PR unless asked.

## Run commands (durable)

```bash
uv --directory services/api run pytest ../../tests/pipelines/test_pipeline.py
cd services/api && uv run pytest
npm test -w uis/web -- --coverage=false --testPathPatterns="reporting|MonthlyClinicSupplyReport"
npm run typecheck -w uis/web
python3 data/pipelines/pipeline.py
```

Last updated: 2026-10-21
