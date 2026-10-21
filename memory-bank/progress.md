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
- CLI `python3 data/pipelines/pipeline.py`: **completed** with `events_extracted=0` (no `SUPABASE_URL`; safe substitute).
- Live `reporting` schema not applied to Supabase.
- Headed dashboard smoke not run (ports 3001/8000 were not listening). Jest covered loading, empty, error, and populated US/UK states.

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

Last updated: 2026-10-19
