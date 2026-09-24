# Context — HealthCore Digital (active)

## Goal

Evidence-based Lighthouse / Web Vitals audit of `uis/website` and `uis/web`. Phase guide: [`Performance-Web-Vitals-Context.md`](../Performance-Web-Vitals-Context.md). Measurement record: [`AUDIT.md`](../AUDIT.md). Results: [`REPORT.md`](../REPORT.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), and FastAPI (8000). **This audit uses host `next start` after `next build`, not Compose `next dev`.**
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
- Baseline Lighthouse screenshots live under `audit/before/` and must stay frozen.
- Do not install optional performance skills unless the user authorizes it.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

Audited URLs: `http://localhost:3000/` (desktop + mobile), `http://localhost:3001/operations` (desktop, authenticated).

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`, `archive/2026-09-18-inventory-backoffice-ui/`, `archive/2026-09-23-docker-compose/`.

## Relevant files

| Path | Role |
|------|------|
| `Performance-Web-Vitals-Context.md` | Phase guide |
| `AUDIT.md` | Protocol, baseline, findings |
| `REPORT.md` | Corrections, refactor, before/after |
| `audit/before/`, `audit/after/` | Lighthouse screenshots |
| `uis/website` | Public site |
| `uis/web` | Staff UI |
| `TESTING.md` | Test commands |
