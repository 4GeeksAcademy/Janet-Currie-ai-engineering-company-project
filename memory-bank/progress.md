# Progress — Active iteration

## Current state

No active implementation. Caching optimisation is archived under [`archive/2026-09-30-caching-optimisation/`](archive/2026-09-30-caching-optimisation/). Durable notes: [`implementation-memory/caching.md`](implementation-memory/caching.md). Trail remains in [`CACHING_REPORT.md`](../CACHING_REPORT.md).

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188), inventory backoffice UI, Docker Compose (`c96f167`), Web Vitals (`ebec7d6`), serialization (`34c1e99`), caching (`341d3d8`).

## Validation results

Standing: caching `uv run pytest` 113 passed; staff Jest 43 passed; typecheck/lint/builds (2026-09-24). Docs-only archive this session: no runtime tests required.

## Blockers

None.

## Next steps

1. Await the next phase.

## Run commands (durable)

```bash
cd services/api && uv run pytest
npm test -w uis/web
npm run typecheck
```

Last updated: 2026-09-30
