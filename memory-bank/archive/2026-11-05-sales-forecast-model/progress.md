# Progress — Active iteration

## Current state

Sales-forecast feasibility pipeline is implemented on `sales-forecast-model`. Holdout report card: **unsupported** (Random Forest MAE does not beat seasonal-naive). Plan: [`docs/sales-forecast/sales-forecast-implementation-plan.md`](../docs/sales-forecast/sales-forecast-implementation-plan.md). Results: [`docs/sales-forecast/sales-forecast.md`](../docs/sales-forecast/sales-forecast.md). Do not push or open a PR unless asked.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline, nightly telemetry export, Redis/Celery message queue.

## Completed (this iteration)

- Isolated `scripts/sales_forecast` uv project and `scripts/train_sales_forecast.py`.
- Causal features, 8/2 split, RF selection, 80% split-conformal interval, metrics, plot, report card.
- Focused tests under `tests/pipelines/test_sales_forecast_*.py`.
- Operator docs with actual holdout numbers.

## Validation results

- `uv --directory scripts/sales_forecast run pytest`: **23 passed** (2026-11-05).
- Training script run 2026-11-05: wrote `data/eval/sales_forecast/{metrics.json,test_predictions.csv,forecast_2024_2025.png}`.
- Test MAE RF $163,235 vs seasonal-naive $161,558 → **unsupported**.
- Gini 0.918; K2 0.044; interval coverage 79.2% of 80% nominal.
- FastAPI suite not run (API untouched). No UI in this ticket.

## Blockers

None.

## Next steps

1. Re-run forecast pytest after the seasonal-naive unit test if not already green in this session.
2. Wait for the user to request a commit.

## Run commands (durable)

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
./services/api/.venv/bin/python scripts/nightly_export.py
docker compose up --build
```

Last updated: 2026-11-05
