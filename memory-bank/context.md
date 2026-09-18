# Context — HealthCore Digital (active)

## Goal

No active course phase. Milestone 5 (HCR-0188) inventory API is complete. Await the next instruction.

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT).
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

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`.

## Relevant files

| Path | Role |
|------|------|
| `memory-bank/implementation-memory/inventory-api.md` | Durable HCR-0188 notes |
| `services/api/app/routers/inventory.py` | `/inventory` router |
| `TESTING.md` | Test commands including HCR-0188 |
