# Progress — Caching optimisation (archived snapshot)

## Current state

Caching optimisation **complete** on `Caching-Optimisation` (`341d3d8`). Report: [`CACHING_REPORT.md`](../../../CACHING_REPORT.md). Durable notes: [`implementation-memory/caching.md`](../../implementation-memory/caching.md). Phase guide archived here.

## Completed

- Timing middleware (`REQUEST_TIMING`); volume seeds (`INVENTORY_LOAD_EXTRA`, `SUPPLIER_LOAD_EXTRA`).
- Cache on `GET /inventory/products` and `GET /inventory/orders` (plus product-by-id); write invalidation; failed outbound 400 does not invalidate.
- Lazy `/operations` and `/incidents`; `deriveMovementRows` `useMemo` in MovementHistory.

## Validation results

- `cd services/api && uv run pytest` — **113 passed** (2026-09-24).
- `npm run typecheck` — pass.
- `npm run lint -w uis/website` / `npm run lint -w uis/web` — no ESLint warnings or errors.
- `npm test -w uis/web -- --coverage=false` — **5 suites, 43 passed**.
- `npm run build -w uis/website` and `npm run build -w uis/web` — pass.
- Products miss/hit median 105.89 ms / 6.16 ms (86 supplies); orders 19.18 ms / 10.54 ms (127 rows).
- Staff production chunks: `/operations` 1.43 kB, `/incidents` 1.44 kB, first load 102 kB vs `/suppliers` 4.46 kB / 108 kB.

Unverified: headed `next start` + live API login; Postgres row-lock path; React Profiler numbers.

## Next steps

Await the next phase.

Last updated: 2026-09-30
