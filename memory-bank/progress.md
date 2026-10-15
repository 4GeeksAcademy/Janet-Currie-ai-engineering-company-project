# Progress — Active iteration

## Current state

On `data-pipeline`. Sprint 1 implemented (design + inbound `unit_cost`). Next: wait for the user to start Sprint 2 (new plan, then approval). Do not implement Prefect or reporting APIs yet.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry.
- Sprint 1 pipeline design: [`data/pipelines/PIPELINE_DESIGN.md`](../data/pipelines/PIPELINE_DESIGN.md).

## Validation results

- `npm test -w uis/web -- --coverage=false --testPathPatterns="src/lib/__tests__/telemetry.test.ts|src/components/inventory/__tests__/inventoryViews.test.tsx"` — **19 passed**.
- `npm run typecheck -w uis/web` — pass.
- No Prefect/reporting code added. Headed login against the inbound form was not run.

## Blockers

None.

## Next steps

1. Commit Sprint 1 (`feat: add business performance pipeline design document`).
2. Stop until the user asks to start Sprint 2.

## Run commands (durable)

```bash
cd services/api && uv run pytest
npm test -w uis/web
npm run typecheck
```

Last updated: 2026-10-14
