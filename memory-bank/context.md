# Context — HealthCore Digital (active)

## Goal

Milestone 5 Part 2: authenticated backoffice inventory views in `uis/web`, talking only to the Part 1 `/inventory` API. Phase guide: root [`Backoffice-Inventory-Interface-Context.md`](../Backoffice-Inventory-Interface-Context.md).

## Scope (this iteration)

- Four protected routes under `/backoffice/inventory/...` in `uis/web` (App Router, port 3001).
- Dedicated `uis/web/src/lib/inventory.ts` client (JWT via existing `apiFetch`; no page-level `fetch`).
- Presentation-only stock badges; official stock comes from the API.
- Do **not** change the inventory backend unless a live contract bug is proven.
- Do **not** add catalogue create/edit/delete UI, history edit/delete, search/pagination, auth redesign, or PHI.

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
- Work lives in `uis/web`, not `uis/backoffice`.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/`, `archive/2026-08-28-supplier-directory/`, `archive/2026-08-28-staff-auth/`, `archive/2026-08-31-error-handling/`, `archive/2026-09-04-bullet-proof/`, `archive/2026-09-18-inventory-api/`.

## Relevant files

| Path | Role |
|------|------|
| `Backoffice-Inventory-Interface-Context.md` | Part 2 phase guide |
| `uis/web/src/lib/inventory.ts` | Inventory types + `apiFetch` helpers |
| `uis/web/src/lib/apiClient.ts` | JWT, timeout vs caller abort |
| `uis/web/src/components/inventory/` | Supplies list, delivery, consumption, history |
| `uis/web/src/app/(protected)/backoffice/inventory/` | Four App Router pages |
| `memory-bank/implementation-memory/inventory-api.md` | Durable HCR-0188 notes |
| `TESTING.md` | Test commands including HCR-0188 |
