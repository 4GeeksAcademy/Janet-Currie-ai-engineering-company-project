# Progress — Active iteration

## Current state

On `telemetry-capture`. Capture stub + `track()` queue implemented. Next after commit: storage plan on `telemetry-storage`.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory UI, Compose, Web Vitals, serialization, caching.
- Telemetry capture (this branch): `POST /telemetry/events` stub; HealthCore catalogue in `docs/telemetry/`; staff `track()` with batch/beacon/retry.

## Validation results

- `uv run pytest` — **118 passed** (2026-09-30).
- `npm test -w uis/web` focused (telemetry/inventoryViews/apiClient/lazyPages) — **26 passed**.
- `npm run typecheck -w uis/web` and lint — pass.

Unverified: headed DevTools batch screenshot against `next start`.

## Blockers

None.

## Next steps

1. Commit `telemetry-capture` (requested by sprint overview).
2. Storage phase plan, then implement.

## Run commands (durable)

```bash
cd services/api && uv run pytest
npm test -w uis/web
npm run typecheck
```

Last updated: 2026-09-30
