# Context — HealthCore Digital (active)

## Goal

Docker development environment (`infra-40`). From the repo root, `docker compose up` starts the public site (3000), staff UI (3001), and FastAPI (8000) with hot reload. Phase guide: root [`Docker-Context.md`](../Docker-Context.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory.
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
- No Postgres/mail containers in this stack. Do not revive leftover `uis/backoffice`. Do not put Dockerfiles under `infra/`.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. npm workspaces share the root lockfile. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; only container-originated calls use Docker DNS `http://backend:8000`.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`, `archive/2026-09-18-inventory-backoffice-ui/`.

## Relevant files

| Path | Role |
|------|------|
| `Docker-Context.md` | Docker / infra-40 phase guide |
| `docker-compose.yml` | `ui` + `backend` on named network `healthcore_dev` |
| `.env.example` | Committed placeholders; copy to gitignored `.env` |
| `uis/Dockerfile`, `uis/start.sh`, `uis/.dockerignore` | Node 20 Alpine image; both Next apps |
| `services/Dockerfile`, `services/.dockerignore` | Python 3.12 + uv; uvicorn reload |
| `.dockerignore` | Repo-root build context exclusions |
| `services/api/app/main.py` | CORS from `CORS_ORIGINS`; `scripts/` on `sys.path` via `parents[3]` |
| `memory-bank/implementation-memory/inventory-api.md` | Durable HCR-0188 notes |
| `memory-bank/implementation-memory/inventory-backoffice-ui.md` | Durable inventory UI notes |
| `TESTING.md` | Test commands including HCR-0188 |
