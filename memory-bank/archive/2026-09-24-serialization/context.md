# Context — HealthCore Digital (active)

## Goal

Backend serialization audit of the existing FastAPI app in [`services/api`](../services/api) is complete. Phase guide: [`Backend-Serialization.md`](../Backend-Serialization.md). Audit trail: [`docs/serialization-audit.md`](../docs/serialization-audit.md).

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
- Stay on the current git branch; no new branch unless asked.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. The public website and `scripts/` do not call this HTTP API.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`, `archive/2026-09-18-inventory-backoffice-ui/`, `archive/2026-09-23-docker-compose/`, `archive/2026-09-23-web-vitals/`.

## Relevant files

| Path | Role |
|------|------|
| `Backend-Serialization.md` | Phase guide |
| `docs/serialization-audit.md` | Required audit matrix |
| `services/api/app/main.py` | FastAPI entry point |
| `services/api/app/routers/` | Application routes |
| `services/api/app/auth/models.py` | Auth/user/profile schemas |
| `uis/web/src/lib/{authApi,inventory,suppliersApi,incidentsApi}.ts` | HTTP consumers |
