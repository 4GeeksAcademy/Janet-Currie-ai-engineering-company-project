# Progress — Active iteration

## Current state

Repository layout aligned with README structure (2026-08-06): company briefing at `CONTEXT.md`, Milestone 1 briefing/spec docs under `docs/`, programming-fundamentals context under `uis/programming-fundamentals/`. Active iteration remains **backend-ready documentation + agent memory alignment**. Frontend Milestone 4 deliverables and the architecture proposal are complete and remain in the tree.

## Completed

- Milestone 1 static site (archived HTML under `uis/`)
- Milestone 2 programming fundamentals (`src/`, demo under `uis/programming-fundamentals/`)
- Milestone 4 agent scaffolding + Next.js website/backoffice
- Backend architecture proposal (`docs/architecture_proposal.md`), including scale/evolution section
- Merged milestone branches into `main` on `Janet-Currie-ai-engineering-company-project`
- Memory bank realigned to global layout; prior files archived under `archive/2026-07-29-monorepo-ai-frontend/`
- Root docs reorganized to match README structure (`CONTEXT.md`, `docs/*`, PF context co-located)

## Validation results

- Website/backoffice previously typechecked and built successfully (2026-07-29).
- This change: docs/layout restructuring only — no app code changed this session.

## Blockers

- None. Backend implementation waiting on explicit user go-ahead.

## Next steps

1. When requested: scaffold `services/healthcore-api` per architecture proposal (health/ready, locations, then analytics parity).
2. Amend `.agents/rules/src-import-only.md` when API owns analytics (as noted in architecture proposal).
3. Keep updating this file after any material work.

## Run commands (durable)

```bash
npm install
npm run dev:website      # :3000
npm run dev:backoffice   # :3001
npm run typecheck
```

Last updated: 2026-08-06
