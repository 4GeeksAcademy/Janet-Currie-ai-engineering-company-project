# Context — HealthCore Digital (active)

## Goal

Operate HealthCore Digital’s monorepo so agents and engineers can safely extend the public website, internal backoffice, and (next) backend APIs without losing company or technical context.

## Scope (active)

- Maintain agent memory bank per global working rules (`context`, `spec`, `progress`, `decisions`, `archive/`).
- Keep shipped UIs runnable: `uis/website`, `uis/backoffice`.
- Treat [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) as the agreed backend blueprint before coding `services/`.
- Do **not** invent production PHI flows or EHR integrations without explicit instruction.

## Constraints

- Company briefing: [`CONTEXT.md`](../CONTEXT.md) (do not edit without instruction).
- Milestone 1 static archives: `uis/index.html`, `uis/application.html`, `uis/validation.js` — reference only.
- Milestone 2 TS under `src/types/**` and `src/utils/**` — import only until API owns analytics (see decisions).
- APIs live only under `services/`.
- HIPAA (US) / UK GDPR apply to any patient-adjacent data handling.
- No commit/push/PR unless the user requests it.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue. Pain points already modeled: claim denials (~14%), no-shows (~22%), CME/licence tracking, fragmented systems.

## Relevant files

| Path | Role |
|------|------|
| `CONTEXT.md` | Company briefing |
| `AGENTS.md` | Project agent operating rules |
| `memory-bank/*` | Active iteration memory |
| `docs/architecture_proposal.md` | Backend architecture decisions |
| `uis/website/` | Public Next.js site |
| `uis/backoffice/` | Internal Next.js ops UI |
| `src/types/`, `src/utils/` | Milestone 2 domain logic (legacy-to-API path) |
| `services/` | Future FastAPI service(s) |
| `.agents/rules/` | Scoped path rules |
| `skills/pre-delivery-verification/` | Pre-commit verification skill |
