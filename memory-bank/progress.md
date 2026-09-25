# Progress — Active iteration

## Current state

Caching optimisation **implemented** on `Caching-Optimisation`. Report: [`CACHING_REPORT.md`](../CACHING_REPORT.md). Durable notes: [`implementation-memory/caching.md`](implementation-memory/caching.md). Not archived until the user asks.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188), inventory backoffice UI, Docker Compose (`c96f167`), Web Vitals (`ebec7d6`), serialization (`34c1e99`).
- Caching: timing middleware; volume seeds; cache on `GET /inventory/products` and `GET /inventory/orders`; lazy `/operations` and `/incidents`; `deriveMovementRows` `useMemo`.

## Validation results

- `cd services/api && uv run pytest` — **113 passed** (2026-09-24).
- `npm run typecheck` — pass.
- `npm run lint -w uis/website` / `npm run lint -w uis/web` — no ESLint warnings or errors.
- `npm test -w uis/web -- --coverage=false` — **5 suites, 43 passed**.
- `npm run build -w uis/website` and `npm run build -w uis/web` — pass.
- Products miss/hit median 105.89 ms / 6.16 ms (86 supplies); orders 19.18 ms / 10.54 ms (127 rows).
- Staff production chunks: `/operations` 1.43 kB, `/incidents` 1.44 kB, first load 102 kB vs `/suppliers` 4.46 kB / 108 kB.

Unverified: headed `next start` + live API login (production server not started in this environment); Postgres row-lock path; React Profiler numbers. Auth-required lazy routes are covered by AuthGuard tests plus Jest loading `role="status"`.

## Blockers

None.

## Next steps

1. Archive this iteration only if asked.

## Run commands (durable)

```bash
cd services/api && uv run pytest
npm test -w uis/web
npm run typecheck
```

Last updated: 2026-09-24
