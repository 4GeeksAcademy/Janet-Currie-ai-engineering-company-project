# Progress — Active iteration

## Current state

No active course phase. Milestone 5 inventory API is complete and archived under [`archive/2026-09-18-inventory-api/`](archive/2026-09-18-inventory-api/).

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188).

## Validation results

HCR-0188 (2026-09-18): 16 inventory pytest passed; 96 full pytest; compileall ok; live seed 6/4/3 gloves 105; live `/docs` + HTTP smoke of evaluator-critical flows. Details in [`TESTING.md`](../TESTING.md).

## Blockers

- None for inventory. Supabase MCP SQL still fails password auth; live checks used SQLAlchemy via `.env`.

## Next steps

1. Await the next instruction.

## Run commands (durable)

```bash
cd services/api
uv sync --group dev
uv run pytest
uv run seed-auth
uv run seed-inventory
uv run uvicorn app.main:app --reload --port 8000
```

Last updated: 2026-09-18
