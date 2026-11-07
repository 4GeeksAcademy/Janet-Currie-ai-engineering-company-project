# Context — HealthCore Digital (archived snapshot)

## Goal

Sales-forecast feasibility on branch `sales-forecast-model`. Phase guide: [`sales-forecast-model-context.md`](sales-forecast-model-context.md). Briefing: [`healthcore-BRIEFING.en.md`](healthcore-BRIEFING.en.md). Durable notes: [`implementation-memory/sales-forecast.md`](../../implementation-memory/sales-forecast.md).

## Scope (standing)

- Keep shipped UIs runnable: `uis/website` (public), `uis/web` (staff JWT, including inventory).
- Phase 1 incident CLI: [`scripts/`](../../../scripts/).
- Phase 2 API: incidents, suppliers, staff JWT auth, inventory, telemetry, reporting, Celery queue.
- Local stack: `docker compose up` starts website (3000), staff UI (3001), FastAPI (8000), Redis (6379), worker, Flower (5555).

## Constraints

- Aggregated monthly revenue only; no patient-level data.
- Do not add ML deps to `services/api/pyproject.toml` or stdlib `scripts/requirements.txt`.
- Do not modify `data/raw/healthcore_sales.csv` or `data/pipelines/pipeline.py`.
- Do not invent US/UK rows or tune on 2024–2025.

## Relevant files

| Path | Role |
|------|------|
| `sales-forecast-model-context.md` | Modeling / leakage contract (this archive) |
| `healthcore-BRIEFING.en.md` | Schema, target, deliverables (this archive) |
| `docs/sales-forecast/sales-forecast.md` | Results and go/no-go |
| `scripts/train_sales_forecast.py` | Training entry |
| `scripts/sales_forecast/` | Isolated uv package |
| `data/raw/healthcore_sales.csv` | Source CSV |
