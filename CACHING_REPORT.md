# Caching report — HealthCore Digital

## 1. Executive summary and scope

This branch reduces **staff-app load** and **inventory-read latency** without adding Redis, HTTP cache headers, or a new backend.

- **Frontend:** `OperationsAnalytics` and `IncidentAnalyzer` are newly lazy-loaded with `next/dynamic` (website `AppointmentModal` is **not** counted). Movement history derives sorted display rows with `useMemo` via `deriveMovementRows`.
- **Backend:** in-process TTL cache on `GET /inventory/products` and `GET /inventory/orders`. Successful inventory writes invalidate; failed writes do not. Auth, profiles, health, and incident CSV are not cached.
- **Evidence:** TestClient medians on sqlite with 86 supplies / 127 movements: products miss **105.9 ms** → hit **6.2 ms**. Production `next build`: `/operations` and `/incidents` page JS **1.43–1.44 kB** (first load 102 kB) vs statically imported `/suppliers` **4.46 kB** (108 kB).
- **Rejected:** `GET /health` (cheap), `GET /auth/me` (personalized), `GET /suppliers` at current volume (~10 ms, 15 canonical rows).

Scope: [`uis/web`](uis/web) + [`services/api`](services/api). Website homepage dynamic-import experiment from Web Vitals is not repeated.

## 2. Environment, build mode, database, dataset

| Item | Value |
|------|--------|
| Branch | `Caching-Optimisation` |
| API | FastAPI 0.141.1 / Pydantic 2.13.4, TestClient (Starlette) |
| Inventory DB | temp sqlite (`tests.helpers` `DATABASE_URL`) |
| Timing logs | `REQUEST_TIMING` default on for local uvicorn; tests set `0` |
| Cache | in-process `TtlCache`, max 512 entries, TTL 30 s |
| Frontend builds | `next build` production; website 15.5.23, staff 15.2.4 |
| Canonical inventory | 6 SKUs, 4 deliveries, 3 consumptions (gloves stock 105) |
| Profile dataset | +80 SKUs (`HCR-LOAD-*`), +80 deliveries, +40 consumptions → **86 supplies, 84 deliveries, 43 consumptions, 127 order rows** |
| Supplier canonical | 15 TinyDB rows (`uv run seed`); extras via `SUPPLIER_LOAD_EXTRA` |
| Pytest DBs | still isolated temp files; volume seed is opt-in |

Reproduce profile inventory:

```bash
cd services/api
uv run seed-auth
INVENTORY_LOAD_EXTRA=80 uv run seed-inventory
```

Canonical `uv run seed-inventory` without the env var is unchanged (6 SKUs). Pytest does not use the volume extras except `test_volume_seed_is_idempotent` (5 extras on a temp sqlite).

## 3. Endpoint assessment

All **27** application routes from `include_router` in [`services/api/app/main.py`](services/api/app/main.py) plus `GET /health`. Paths match OpenAPI / `JSON_ROUTES` + `SPECIAL_ROUTES`. Decision column is **after** timing. Frequency is staff-UI expected use, not production traffic.

| Method | Path | Auth | Store / cost | Change rate | User-varying / sensitive | Decision |
|--------|------|------|--------------|-------------|--------------------------|----------|
| GET | `/health` | none | none, trivial | n/a | no | **No** — median ~13 ms |
| POST | `/auth/login` | none | TinyDB + JWT | n/a | credentials | **No** — auth |
| GET | `/auth/me` | bearer | TinyDB | low | **yes** email | **No** — personalized |
| POST | `/auth/forgot-password` | none | email side effect | n/a | email in | **No** |
| POST | `/auth/reset-password` | none | write | n/a | token | **No** |
| POST | `/auth/change-password` | bearer | write | n/a | passwords | **No** |
| POST | `/users` | none | TinyDB write | n/a | password in | **No** — write |
| GET | `/users` | bearer | TinyDB list | low | emails | **No** — PII list |
| GET | `/users/{user_id}` | self/admin | TinyDB | low | email | **No** |
| PUT | `/users/{user_id}` | self/admin | write | n/a | | **No** |
| DELETE | `/users/{user_id}` | self/admin | write | n/a | | **No** |
| GET | `/profiles/me` | bearer | TinyDB | medium | phone/address | **No** |
| PUT | `/profiles/me` | bearer | write | n/a | | **No** |
| POST | `/api/incidents/analyze` | bearer | CSV CPU | n/a | upload | **No** |
| GET | `/api/incidents/results/export` | bearer | last analysis | per upload | process-global CSV | **No** |
| POST | `/suppliers` | bearer | TinyDB write | n/a | | **No** (would invalidate lists) |
| GET | `/suppliers` | bearer | TinyDB scan + filters | medium | staff directory | **No** at current volume (~10 ms) |
| GET | `/suppliers/{supplier_id}` | bearer | TinyDB get | medium | | **No** |
| PATCH | `/suppliers/{supplier_id}` | bearer | write | n/a | | **No** |
| PATCH | `/suppliers/{supplier_id}/rate` | bearer | write | n/a | | **No** |
| PATCH | `/suppliers/{supplier_id}/status` | bearer | write | n/a | | **No** |
| GET | `/inventory/products` | bearer | SQLModel **1+2N** stock sums | high when moving stock | shared catalogue | **Yes** |
| POST | `/inventory/products` | bearer | write | n/a | | **No** (invalidates) |
| GET | `/inventory/products/{supply_id}` | bearer | 2 stock queries | high | shared | Cached; same invalidation as list |
| POST | `/inventory/orders/inbound` | bearer | write | n/a | | **No** (invalidates on success) |
| POST | `/inventory/orders/outbound` | bearer | write + stock check | n/a | | **No** (invalidates on success; 400 does not) |
| GET | `/inventory/orders` | bearer | 3 table scans + in-memory join | high | same list for all staff | **Yes** |

Invalidation matrix (after successful commit only):

| Write | Invalidate |
|-------|------------|
| `POST /inventory/products` | products list + that product id + orders list |
| `POST /inventory/orders/inbound` | products list, that product id, orders list |
| `POST /inventory/orders/outbound` (201) | products list, that product id, orders list |
| Failed/rolled-back writes, 4xx/5xx | none |

## 4. Baseline methodology and results

Backend: TestClient, sqlite profile dataset, seven samples, **median**. Cold = cache cleared before each GET (miss / uncached path). Warm = after one populate.

| Endpoint | Dataset | Miss median | Hit median |
|----------|---------|-------------|------------|
| `GET /inventory/products` | 86 rows | **105.89 ms** | **6.16 ms** |
| `GET /inventory/orders` | 127 rows | **19.18 ms** | **10.54 ms** |
| `GET /health` | n/a | 12.81 ms | n/a (uncached) |
| `GET /suppliers` | 5–15 rows in this TestClient DB | 9.95 ms | n/a |
| `GET /auth/me` | 1 user | 8.56 ms | n/a |

Products miss is in the brief’s 100–200 ms investigation band. `list_supplies` was called once per cold run (7/7). Hits skip that function (`test_list_products_miss_then_hit_skips_service`).

These are TestClient lab numbers, not multi-worker production.

Frontend: production `next build` (not `next dev`). Staff route table (2026-09-24):

| Route | Page size | First Load JS |
|-------|-----------|----------------|
| `/operations` | 1.43 kB | 102 kB |
| `/incidents` | 1.44 kB | 102 kB |
| `/suppliers` (still static import) | 4.46 kB | 108 kB |
| `/backoffice/inventory/orders` | 3.28 kB | 107 kB |

Lazy routes omit the `261-*.js` chunk that static staff islands pull into the page graph. First load is ~5–6 kB smaller than `/suppliers`.

## 5. Frontend lazy loading

**Selected**

1. [`uis/web/src/app/(protected)/operations/page.tsx`](uis/web/src/app/(protected)/operations/page.tsx) → `OperationsAnalytics` (`next/dynamic`, accessible `role="status"` loading copy, `min-h-[24rem]`).
2. [`uis/web/src/app/(protected)/incidents/page.tsx`](uis/web/src/app/(protected)/incidents/page.tsx) → `IncidentAnalyzer`, same loading pattern.

Why: route-only, heavy (analytics pulls `@healthcore/*`; incidents is CSV UI). Not needed on login, welcome, or inventory.

Not selected: `AppointmentModal` (already dynamic). Homepage sections (prior LCP regression). `AuthGuard` / `AuthProvider`.

Jest: [`lazyPages.test.tsx`](uis/web/src/app/(protected)/__tests__/lazyPages.test.tsx) asserts the loading `role="status"` text. Headed browser login against `next start` was **not** run in this session (no live 3001 stack); loading/auth contracts are covered by Jest + existing AuthGuard tests.

## 6. Memoized computation

[`deriveMovementRows`](uis/web/src/lib/inventory.ts) copies the movement list, sorts newest-first (date, then kind, then id), and maps labels. [`MovementHistory`](uis/web/src/components/inventory/MovementHistory.tsx) wraps it in `useMemo(..., [data])`. Fetching still uses `useAsyncResource`.

Dependencies: only `data` from the hook. The helper is pure and does not mutate `data`.

Tests: empty input, sort/labels, source-array unchanged, replaced input set ([`inventory.test.ts`](uis/web/src/lib/__tests__/inventory.test.ts)). Existing MovementHistory view tests still pass.

Benefit: avoids re-sorting 100+ rows on unrelated parent renders. Estimated; not a React Profiler capture in this session.

## 7. Cached endpoints

### `GET /inventory/products`

| Field | Value |
|-------|--------|
| Key | `v1:inventory:products:list` (no user/token/email) |
| Item key | `v1:inventory:products:id:{supply_id}` |
| Value | JSON-mode dump of `MedicalSupplyPublic`; re-validated on hit |
| TTL | 30 s safety bound (`INVENTORY_TTL_SECONDS`) |
| Invalidate | `POST /inventory/products`, inbound, outbound (after commit) |
| Auth | handler still requires JWT; cache is shared **catalogue** (same body for all staff) |
| Cold/warm | 105.89 ms / 6.16 ms median (86 rows) |

### `GET /inventory/orders`

| Field | Value |
|-------|--------|
| Key | `v1:inventory:orders:list` |
| Value | JSON dump of `OrderMovement` including nested `SupplySummary` |
| TTL | 30 s |
| Invalidate | same inventory writes |
| Cold/warm | 19.18 ms / 10.54 ms median (127 rows) |

Failed outbound (insufficient stock) does **not** invalidate (`test_failed_outbound_does_not_invalidate`). 404 product GETs are not stored. 401 never reaches the cache.

## 8. Freshness vs performance

Staff can tolerate a few seconds of stale stock **if** the API also invalidates on every successful movement. TTL 30 s is only for missed invalidation (crash between commit and `invalidate_*`, or out-of-band SQL). Shorter TTL would cut the products win (106 ms → 6 ms) if invalidation were omitted; we keep both.

## 9. Considered and rejected

- **`GET /health`:** ~13 ms, public, no derived work.
- **`GET /auth/me`:** personalized email/profile; shared cache forbidden.
- **`GET /suppliers`:** hypothesis in the brief; ~10 ms with the current TinyDB directory. Caching would need prefix-invalidation across every filter combo for little gain. Revisit if `SUPPLIER_LOAD_EXTRA` is used in production-like volume **and** timings enter the 100 ms band.
- **Redis:** Compose has two app services and no Redis. In-process is enough for one uvicorn worker locally.
- **`functools.lru_cache`:** no TTL, no invalidation, process-global mutable risk.

## 10. Limitations

- **Multi-worker / replicas:** each process has its own dict; invalidation is not cross-process.
- **Restart:** cache empty (correct).
- **External SQL/TinyDB edits:** visible only after TTL or process restart.
- **Stampede:** lock wraps get/set, not compute; concurrent misses can both populate.
- **TestClient vs network:** numbers exclude HTTP and Postgres.
- **`REQUEST_TIMING`:** structured `method/path/status/elapsed_ms` only; no bodies or tokens.

## 11. Validation (actually run, 2026-09-24)

| Command | Result |
|---------|--------|
| `cd services/api && uv run pytest` | **113 passed** |
| `npm run typecheck` | pass (website + web) |
| `npm run lint -w uis/website` | No ESLint warnings or errors |
| `npm run lint -w uis/web` | No ESLint warnings or errors |
| `npm test -w uis/web -- --coverage=false` | **5 suites, 43 passed** |
| `npm run build -w uis/website` | pass |
| `npm run build -w uis/web` | pass; operations/incidents split as above |

Focused cache tests: [`tests/test_cache_inventory.py`](services/api/tests/test_cache_inventory.py). Serialization suite still in the 113.

**Unverified:** headed `next start` + live API login (production server not started in this environment); React Profiler numbers; Postgres `SELECT FOR UPDATE` path (sqlite tests only). Auth-required lazy routes are covered by AuthGuard tests plus Jest `role="status"` loading copy.

Pre-existing: Starlette/`httpx` TestClient deprecation warning.
