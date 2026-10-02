# Spec — Caching optimisation (archived snapshot)

## Requirements

Profile first; two new staff lazy-loads; one non-trivial `useMemo`; TTL cache on at least two FastAPI reads with write invalidation; no shared cache of personalized/sensitive data; trail in [`CACHING_REPORT.md`](../../../CACHING_REPORT.md).

## Acceptance criteria

- [x] Every FastAPI endpoint assessed for cache suitability; realistic-data profiling recorded.
- [x] At least two new staff components/routes lazy-loaded (`next/dynamic`); `AppointmentModal` not recounted.
- [x] At least one non-trivial `useMemo` with complete dependencies; `useAsyncResource` preserved.
- [x] At least two GET endpoints use TTL cache; successful writes invalidate; failures do not; no shared PII/session cache.
- [x] Focused tests (hit/miss/TTL/invalidation/isolation) plus `CACHING_REPORT.md` with rejected candidate and measured results.
- [x] Existing auth, inventory, suppliers, incidents, Web Vitals, and serialization behavior intact.

## Validation

- `cd services/api && uv run pytest` — 113 passed (2026-09-24).
- `npm run typecheck`; lint both UIs; `npm test -w uis/web` — 43 passed; production builds both UIs.
