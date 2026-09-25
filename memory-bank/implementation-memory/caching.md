# Caching optimisation

## Purpose

Cut staff-app first-load JavaScript on unused islands and skip repeated inventory stock/join work on hot GETs, with measured evidence in [`CACHING_REPORT.md`](../../CACHING_REPORT.md).

## Final Behavior

- `/operations` lazy-loads `OperationsAnalytics`; `/incidents` lazy-loads `IncidentAnalyzer` (`next/dynamic`, accessible `role="status"` loading). Website `AppointmentModal` is unchanged and not counted.
- `MovementHistory` memoizes `deriveMovementRows(data ?? [])` with `[data]` only. `useAsyncResource` still fetches.
- `GET /inventory/products` and `GET /inventory/orders` (plus product-by-id) use an in-process TTL cache. Successful inventory writes invalidate; failed outbound 400 and 404s do not populate or invalidate. Auth, profiles, health, and incident CSV are not cached.

## Architecture and Data Flow

Handlers still require JWT. Cache keys are **shared catalogue** strings (`v1:inventory:products:list`, `v1:inventory:products:id:{id}`, `v1:inventory:orders:list`) — no token, email, or `user_id`. Values are JSON dumps of existing Pydantic public models; hits re-validate with `model_validate`. `TtlCache` uses a monotonic clock, `threading.Lock`, deepcopy on get/set, max 512 entries. TTL 30 s is a safety net on top of write invalidation. `REQUEST_TIMING` middleware logs method, route template, status, elapsed ms (default on locally; tests set `REQUEST_TIMING=0`). Cache clears on FastAPI lifespan shutdown and in pytest fixtures.

Idempotent volume seed: `INVENTORY_LOAD_EXTRA`, `SUPPLIER_LOAD_EXTRA`. Canonical six SKUs / 15 suppliers stay the default.

## Important Files

- `services/api/app/cache.py` — `TtlCache` and inventory key helpers
- `services/api/app/middleware.py` — request timing
- `services/api/app/routers/inventory.py` — get/set/invalidate
- `services/api/app/inventory/seed.py` — `seed_inventory_volume`
- `services/api/app/seed.py` — skip-existing + `seed_suppliers_volume`
- `uis/web/src/app/(protected)/operations/page.tsx`, `incidents/page.tsx`
- `uis/web/src/lib/inventory.ts` — `deriveMovementRows`
- `uis/web/src/components/inventory/MovementHistory.tsx`
- `services/api/tests/test_cache_inventory.py`
- `CACHING_REPORT.md`

## Interfaces and Contracts

Cached bodies must match uncached `MedicalSupplyPublic` / `OrderMovement` (including nested `SupplySummary`). Do not cache 4xx/5xx. Serialization secret-field rules still apply.

Env: `REQUEST_TIMING` (`1` default, `0`/`false`/`off`/`no` disables); `INVENTORY_LOAD_EXTRA`; `SUPPLIER_LOAD_EXTRA`.

## Decisions and Constraints

- In-process TTL, not Redis / `functools.lru_cache` / HTTP cache headers.
- Do not lazy-load homepage server sections (prior LCP regression) or the auth shell.
- Do not recount `AppointmentModal` or `SupplierDirectory` country/category `useMemo`.
- Do not mutate host `data/suppliers.json` during profiling unless extras are requested via env.

## Validation

- `cd services/api && uv run pytest` — 113 passed (2026-09-24)
- `npm test -w uis/web -- --coverage=false` — 43 passed
- `npm run typecheck`, lint both UIs, production builds both UIs
- Products miss/hit median 105.89 ms / 6.16 ms (86 supplies); orders 19.18 ms / 10.54 ms (127 rows)
- Staff `next build`: `/operations` 1.43 kB, `/incidents` 1.44 kB first-load 102 kB vs `/suppliers` 4.46 kB / 108 kB

Unverified: headed login against `next start`; Postgres `SELECT FOR UPDATE`; React Profiler numbers.

## Maintenance Notes

When adding cached GETs, keep keys version-prefixed, copy-on-get, invalidate from a helper after commit, and add hit/miss/TTL/write-fail tests. Multi-worker and out-of-band SQL edits are not coherent until TTL or restart. Pytest must keep `response_cache.clear()` so tests do not leak across files.
