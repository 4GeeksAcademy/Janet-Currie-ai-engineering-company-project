# Progress — Active iteration

## Current state

Phase 2 incident analyzer is integrated: FastAPI under `services/api`, backoffice page at `/incidents`, shared logic from `incidents-analysis/`. Broader `healthcore-api` modular monolith remains future work per the architecture proposal.

## Completed

- Milestone 1 static site (archived HTML under `uis/`)
- Milestone 2 programming fundamentals (`src/`, demo under `uis/programming-fundamentals/`)
- Milestone 4 agent scaffolding + Next.js website/backoffice
- Backend architecture proposal (`docs/architecture_proposal.md`), including scale/evolution section
- Incident CSV analyzer CLI (`incidents-analysis/`)
- Phase 2 platform integration: `services/api` analyze/export + `uis/backoffice` `/incidents` UI

## Validation results

- `incidents-analysis`: 17 unit tests OK
- `services/api`: 7 API tests OK (graded fixture 100/94/6; no `PAT-` in JSON/export)
- Backoffice `tsc --noEmit` OK
- Smoke: live `POST /api/incidents/analyze` + `GET .../export` against graded CSV (100/94/6, avg 3.58, no PHI)

## Blockers

- None.

## Next steps

1. When requested: expand toward `services/healthcore-api` modular monolith (locations, analytics parity).
2. Optionally persist analyses (replace in-memory store) and add auth scopes.
3. Keep updating this file after any material work.

## Run commands (durable)

```bash
npm install
npm run dev:website      # :3000
npm run dev:backoffice   # :3001
npm run typecheck

cd services/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

cd incidents-analysis
python3 analyze.py incidents-healthcore.csv --no-export
python3 -m unittest discover -s tests -v
```

Last updated: 2026-08-06
