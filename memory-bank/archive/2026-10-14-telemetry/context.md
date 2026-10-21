# Context — HealthCore Digital (archived snapshot)

## Goal

Telemetry sprint (capture → storage → report) on `telemetry-capture`, `telemetry-storage`, and `telemetry-report`. Phase guide: [`Telemetry-Context.md`](Telemetry-Context.md). Durable notes: [`implementation-memory/telemetry.md`](../../implementation-memory/telemetry.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../../../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), and FastAPI (8000).
- Treat [`docs/architecture_proposal.md`](../../../docs/architecture_proposal.md) as the blueprint before expanding beyond Phase 2.
- Do **not** invent production PHI flows or EHR integrations without explicit instruction.

## Constraints

- Company briefing: [`CONTEXT.md`](../../../CONTEXT.md) (do not edit without instruction).
- Milestone 1 static archives and Milestone 2 `src/types/**`, `src/utils/**` — import only until instructed.
- APIs live only under `services/`.
- HIPAA (US) / UK GDPR apply to any patient-adjacent data handling.
- User/Profile stay in TinyDB only (`services/api/data/auth.json`). Do not add User/Profile tables in Postgres/Supabase.
- No commit/push/PR unless the user requests it.
- Staff UI is `uis/web`, not `uis/backoffice`. No PII/PHI in telemetry. Preserve leftover `uv.lock` / `.coverage`.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

## Relevant files

| Path | Role |
|------|------|
| `Telemetry-Context.md` | HealthCore telemetry design handoff |
| `docs/telemetry/` | Plan, JSON schemas, phase implementation plans, SQL |
| `services/api/app/telemetry/` | Envelope, store, Pandas analysis |
| `uis/web/src/lib/telemetry.ts` | Single `track()` + queue |
