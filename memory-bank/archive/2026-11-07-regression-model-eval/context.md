# Context — HealthCore Digital (active)

## Goal

Evaluate the existing HealthCore monthly revenue random forest for underfitting, overfitting, or a reasonable fit. The 2024–2025 holdout stays unused. Archived 2026-11-07 with this folder.

## Scope (this iteration)

- Training-period evaluation only, on branch `regression-model-eval`.
- Five expanding year folds (validation years 2019–2023), MAE and RMSE, sample standard deviation.
- Frozen forest from `data/eval/sales_forecast/metrics.json` (100 trees, depth 5, `min_samples_leaf` 2, seed 42).
- Learning curve at `data/eval/sales_forecast/learning_curve.png`.
- Report at `data/eval/evaluation_report.md`.
- Do not retune, deploy, or add ML dependencies to the API.

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting, Celery queue.
- Sales forecast CLI: [`scripts/train_sales_forecast.py`](../scripts/train_sales_forecast.py) and [`scripts/eval_sales_forecast.py`](../scripts/eval_sales_forecast.py) (isolated `scripts/sales_forecast` uv env).
- Local stack: `docker compose up` starts website (3000), staff UI (3001), FastAPI (8000), Redis (6379), worker, Flower (5555).
- Treat [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) as the blueprint before expanding beyond Phase 2.
- Do **not** invent production PHI flows or EHR integrations without explicit instruction.

## Constraints

- Company briefing: [`CONTEXT.md`](../CONTEXT.md) (do not edit without instruction).
- Milestone 1 static archives and Milestone 2 `src/types/**`, `src/utils/**` — import/reference only until instructed.
- APIs live only under `services/`.
- HIPAA (US) / UK GDPR apply to any patient-adjacent data handling.
- User/Profile stay in TinyDB only (`services/api/data/auth.json`).
- No commit/push/PR unless the user requests it.
- Treat implementation and validation as one task (see spec).
- Do not rewrite `memory-bank/archive/`. Leave `services/api/.coverage` untracked.
- Celery module is `app.celery_app`. Do not `load_dotenv` at Celery import time.
- Do not add ML deps to `services/api/pyproject.toml` or stdlib `scripts/requirements.txt`.

## Essential background

HealthCore: 12 outpatient clinics (US + UK), ~200 staff, ~$28M revenue.

Staff UI is `uis/web` (port 3001), not `uis/backoffice`. FastAPI lives at `services/api`. Browser API calls use `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

Completed iterations (do not load unless asked): `archive/2026-07-29-monorepo-ai-frontend/` through `archive/2026-11-05-sales-forecast-model/`.

## Relevant files

| Path | Role |
|------|------|
| `CONTEXT.md` | Canonical company briefing |
| `regression-model-eval-context.md` | Evaluation handoff, stored in this archive folder |
| `scripts/sales_forecast/sales_forecast/evaluation.py` | Training-period folds, diagnosis, report |
| `data/eval/evaluation_report.md` | Fit diagnosis and staging sentence |
| `docs/architecture_proposal.md` | Backend blueprint |
| `memory-bank/implementation-memory/index.md` | Durable implementation catalog |
