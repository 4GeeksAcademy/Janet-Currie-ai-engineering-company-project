# Decisions — Caching optimisation (archived snapshot)

## Adopted

| Decision | Rationale |
|----------|-----------|
| Caching uses in-process TTL, not Redis | Compose has no Redis; brief forbids adding infrastructure without measured need |
| Do not cache `/health`, writes, auth/me, profiles, or incident CSV | Personalized, mutating, or upload/export payloads are unsafe or not reusable |
| Do not recount website `AppointmentModal` as a new lazy-load | Already `next/dynamic`; homepage below-fold dynamic imports delayed LCP |
| Cache `GET /inventory/products` and `GET /inventory/orders` (plus product-by-id) | Profiled: products miss ~106 ms from 1+2N stock queries; orders join/serialize |
| Reject `GET /suppliers` at current TinyDB volume | ~10 ms; filter-key invalidation cost exceeds benefit |
| TTL 30 s plus write invalidation | Staff freshness after movements; TTL covers missed invalidation / out-of-band SQL |
| Cache keys omit user/token/email | Catalogue payloads do not vary by staff identity |
| Lazy-load `OperationsAnalytics` and `IncidentAnalyzer` | Route-only heavy islands; production page JS 1.43–1.44 kB vs static `/suppliers` 4.46 kB |
| `useMemo` on `deriveMovementRows` in MovementHistory | Pure sort/label of expanded movement lists; not the existing supplier filter |

## Rejected

| Alternative | Why rejected |
|-------------|--------------|
| Redis / HTTP cache headers / service workers | No multi-process proof locally |
| Cache `GET /health` or `GET /auth/me` | Health is cheap; me is personalized |
| `functools.lru_cache` | No TTL, no invalidation |
