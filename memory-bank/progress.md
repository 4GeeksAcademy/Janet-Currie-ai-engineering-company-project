# Progress — Active iteration

## Current state

On `data-pipeline`. Sprint 2 implemented (Prefect ETL + `/reporting` API). Next: wait for the user to start Sprint 3 (new plan, then approval). Do not add subflows or the dashboard yet.

## Completed (standing)

- Sprint 1 design + inbound `unit_cost`.
- Sprint 2: `data/pipelines/pipeline.py`, `docs/pipelines/reporting.sql`, JWT reporting routes.

## Validation results

- Focused pytest (pipeline + reporting + serialization): **18 passed**.
- Full `uv run pytest`: **138 passed**.
- CLI `python3 data/pipelines/pipeline.py`: **completed** with `events_extracted=0` (no `SUPABASE_URL`; safe substitute, not a live warehouse load).
- Live `reporting` schema not applied to Supabase.

## Blockers

None.

## Next steps

1. Stop until the user asks to start Sprint 3.
2. Do not push or open a PR unless asked.

## Run commands (durable)

```bash
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
```

Last updated: 2026-10-14
