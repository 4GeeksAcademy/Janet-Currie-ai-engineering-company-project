# Context — HealthCore Digital (active)

## Goal

Telemetry **capture** on branch `telemetry-capture`. Contract: [`Telemetry-Context.md`](../Telemetry-Context.md), [`docs/telemetry/telemetry-plan.md`](../docs/telemetry/telemetry-plan.md), [`docs/telemetry/event-schemas.json`](../docs/telemetry/event-schemas.json). Capture implementation: [`docs/telemetry/capture-implementation-plan.md`](../docs/telemetry/capture-implementation-plan.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), and FastAPI (8000).
- Treat [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) as the blueprint before expanding beyond Phase 2.
- Do **not** invent production PHI flows or EHR integrations without explicit instruction.

## Constraints

- Company briefing: [`CONTEXT.md`](../CONTEXT.md) (do not edit without instruction).
- Milestone 1 static archives and Milestone 2 `src/types/**`, `src/utils/**` — import/reference only until instructed.
- APIs live only under `services/`.
- HIPAA (US) / UK GDPR apply to any patient-adjacent data handling.
- User/Profile stay in TinyDB only (`services/api/data/auth.json`). Do not add User/Profile tables in Postgres/Supabase.
- No commit/push/PR unless the user requests it.
- Treat implementation and validation as one task (see spec). Do not rewrite `memory-bank/archive/`.
- Do not rewrite error handlers, replace FastAPI/Pydantic/SQLModel/TinyDB, or create a new backend.
- Stay on `telemetry-capture` until this phase is committed. Do not start storage/report on this branch. Preserve leftover `uv.lock` / `.coverage`.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. The public website and `scripts/` do not call this HTTP API.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`, `archive/2026-09-18-inventory-backoffice-ui/`, `archive/2026-09-23-docker-compose/`, `archive/2026-09-23-web-vitals/`, `archive/2026-09-24-serialization/`, `archive/2026-09-30-caching-optimisation/`.

## Relevant files

| Path | Role |
|------|------|
| `Telemetry-Context.md` | HealthCore telemetry design handoff |
| `docs/telemetry/` | Plan, JSON schemas, capture implementation plan |
| `services/api/app/telemetry/` | Envelope models |
| `uis/web/src/lib/telemetry.ts` | Single `track()` + queue |
| `CACHING_REPORT.md` | Caching investigation trail (keep at repo root) |
| `docs/serialization-audit.md` | FastAPI response contracts |
| `docs/architecture_proposal.md` | Future backend blueprint |
| `services/api/app/main.py` | FastAPI entry |
| `uis/web/` | Staff JWT app |
| `uis/website/` | Public site |
