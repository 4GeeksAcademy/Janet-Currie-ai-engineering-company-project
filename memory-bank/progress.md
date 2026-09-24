# Progress — Active iteration

## Current state

Backend serialization audit is **complete**. Trail: [`docs/serialization-audit.md`](../docs/serialization-audit.md). All 27 application routes are compliant.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188), inventory backoffice UI, Docker Compose dev stack (`c96f167`), Web Vitals audit (`ebec7d6`).
- Serialization: explicit `response_model` on every JSON route; `UserRegisteredResponse` without email on `POST /users`; `HealthResponse`; `IncidentAnalysisResponse`; CSV and 204 contracts documented.

## Validation results

Standing: HCR-0188, inventory UI, infra-40, Web Vitals as previously recorded.

Serialization (2026-09-23): `cd services/api && uv run pytest` — **104 passed**. New `tests/test_serialization_audit.py`. `/docs` + OpenAPI smoke: `TokenResponse`, `UserRegisteredResponse` (no email), `OrderMovement.supply` → `SupplySummary`. UI types unchanged; Jest/typecheck not run.

## Blockers

None.

## Next steps

Await the next phase (serialization is committed on this branch when published).

## Run commands (durable)

```bash
cd services/api && uv run pytest
npm test -w uis/web
npm run typecheck
```

Last updated: 2026-09-23
