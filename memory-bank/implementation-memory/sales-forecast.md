# Sales forecast (feasibility)

## Purpose

Decide whether HealthCore’s aggregated monthly revenue can predict next month well enough to support a future executive dashboard.

## Final Behavior

`scripts/train_sales_forecast.py` loads `data/raw/healthcore_sales.csv`, splits 2016–2023 / 2024–2025, trains a rolling one-month-ahead `RandomForestRegressor` (seed 42), and writes metrics, predictions, and a 2024–2025 plot with an 80% split-conformal interval. The 2026-11-05 holdout did **not** beat seasonal-naive MAE, so the report card is unsupported.

## Architecture and Data Flow

Raw CSV → schema checks → chronological split → causal features on the full series → year-blocked RF selection inside train (calibration window held out) → conformal quantile on last 24 training months → refit on all training feature rows → one-step test scoring → `data/eval/sales_forecast/`. Isolated `uv` project under `scripts/sales_forecast/`. Does not call the FastAPI app.

## Important Files

- `scripts/train_sales_forecast.py`
- `scripts/sales_forecast/`
- `tests/pipelines/test_sales_forecast_*.py`
- `data/raw/healthcore_sales.csv`
- `docs/sales-forecast/sales-forecast.md`

## Interfaces and Contracts

Target `revenue_usd`. Same-month `visits_count` and `avg_revenue_per_visit_usd` are excluded. Gini is ranking Gini; K2 is D’Agostino–Pearson on residuals; PSI is on `visits_count` train vs test.

## Decisions and Constraints

Game A (one-month-ahead). Report-card go/no-go with no dollar cutoff. Random Forest, not XGBoost. Do not invent US/UK rows. Do not add ML deps to the API.

## Validation

`uv --directory scripts/sales_forecast run pytest`. Training script produces `data/eval/sales_forecast/metrics.json`.

## Maintenance Notes

Re-run the training script after feature or metric changes. Do not tune on 2024–2025. Phase guide and briefing live in [`archive/2026-11-05-sales-forecast-model/`](../archive/2026-11-05-sales-forecast-model/).
