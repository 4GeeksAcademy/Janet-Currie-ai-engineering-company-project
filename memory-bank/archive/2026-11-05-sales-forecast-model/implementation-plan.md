# Sales forecast model — implementation plan

Feasibility experiment: can HealthCore’s historical monthly revenue predict **next month** well enough to support a future executive dashboard? Local training/evaluation only — not a dashboard, API, or served model.

Contracts: [`healthcore-BRIEFING.en.md`](healthcore-BRIEFING.en.md) then [`sales-forecast-model-context.md`](sales-forecast-model-context.md). Source: [`data/raw/healthcore_sales.csv`](../../../data/raw/healthcore_sales.csv). Branch: `sales-forecast-model`.

Approved 2026-11-05: Game A (rolling one-month-ahead); report-card go/no-go; ranking Gini; D’Agostino–Pearson K²; PSI on `visits_count`; Random Forest with seed 42; seasonal-naive baseline; 80% split-conformal interval; isolated `uv` project under `scripts/sales_forecast/`.

This file is the execution record. Do not edit the Cursor plan file. Git commit/push/PR only when the user authorizes them.

## Locked decisions

- **Game A:** rolling one-month-ahead. Each 2024–2025 month is predicted using only information available through the previous month.
- **Report card:** no invented dollar cutoff. Supported / unsupported / uncertain from (1) beat seasonal-naive MAE, (2) Gini ranking, (3) interval coverage. If the model loses to last year on MAE, the answer is no.
- **Gini:** normalized ranking Gini of predicted vs actual `revenue_usd`. Not classification ROC.
- **K2:** `scipy.stats.normaltest` (D’Agostino–Pearson K²) on test residuals. Not R². R² is a supporting sklearn metric.
- **PSI:** `visits_count`, train = reference, test = current, bin edges from train only. Do not synthesize US/UK rows.
- **Model:** `RandomForestRegressor(random_state=42)`. No XGBoost. No feature scaling (trees).
- **Baseline:** seasonal naive `ŷ_t = y_{t-12}`.
- **Interval:** 80% split conformal on the last 24 training months. Test coverage does not retune the interval.
- **Seed:** 42.
- **Branch:** `sales-forecast-model`.

## Layout

- `scripts/train_sales_forecast.py` — briefing-required entry.
- `scripts/sales_forecast/` — package + isolated `pyproject.toml` (pandas, scikit-learn, scipy, matplotlib, pytest).
- `tests/pipelines/test_sales_forecast_split.py` — required 8/2 split test. Extra focused tests alongside.
- `data/process/sales_forecast/` — feature/prediction intermediates.
- `data/eval/sales_forecast/` — `metrics.json`, `test_predictions.csv`, `forecast_2024_2025.png`.
- `docs/sales-forecast/sales-forecast.md` — commands, formulas, actual results, conclusion.

Do not modify `data/raw/healthcore_sales.csv`, `data/pipelines/pipeline.py`, FastAPI, Compose, `uis/`, `CONTEXT.md`, `src/types/**`, `src/utils/**`, `services/api/pyproject.toml`, or `scripts/requirements.txt`.

## Leakage rules

- Target: `revenue_usd` from `region == "consolidated"`.
- Split: train 2016–2023, test 2024–2025. Chronological. `max(train.month) < min(test.month)`.
- Exclude same-month `visits_count`, `avg_revenue_per_visit_usd`, and `region`.
- Allowed: calendar month (number + sin/cos), monotonic time index, revenue lag 1 and 12, shifted rolling means 3 and 12, lagged `visits_count` only.
- Hyperparameters chosen only inside training years (excluding the 24-month calibration window). Test scored once.

## Training procedure

1. Validate schema and grain; fail fast.
2. Split by complete calendar years.
3. Causal features; drop rows lacking lag-12.
4. Year-blocked / expanding-window selection inside train, compact RF grid, pick by validation MAE vs seasonal-naive on the same folds.
5. Calibrate 80% conformal quantile on last 24 training months; refit point model on all training feature rows.
6. Score 24 test months rolling one-step.
7. Report MSE, MAE, RMSE, RMSE/mean×100, R², Gini, K2, PSI, baseline errors, interval coverage/width.
8. Plot 2024–2025 actuals, predictions, and 80% band.
9. Write metrics metadata and the report-card conclusion.

## Out of scope

Executive dashboard, model serving, FastAPI/Compose/Celery, XGBoost, synthetic regional series, tuning on 2024–2025, PHI, git publish.
