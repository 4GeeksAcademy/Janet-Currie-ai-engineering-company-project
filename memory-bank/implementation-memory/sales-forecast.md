# Sales forecast (feasibility and fit evaluation)

## Purpose

Decide whether HealthCore’s aggregated monthly revenue can predict next month well enough to support a future executive dashboard, and whether the frozen forest is underfitting, overfitting, or reasonably well fitted.

## Final Behavior

`scripts/train_sales_forecast.py` loads `data/raw/healthcore_sales.csv`, splits 2016–2023 / 2024–2025, trains a rolling one-month-ahead `RandomForestRegressor` (seed 42), and writes metrics, predictions, and a 2024–2025 plot with an 80% split-conformal interval. The 2026-11-05 holdout did **not** beat seasonal-naive MAE, so the report card is unsupported.

`scripts/eval_sales_forecast.py` scores that same frozen forest on training years only. Five expanding validation years are 2019–2023. The 2026-11-06 run classified the fit as overfitting: the 2022–2023 gap ratio was 0.74, so the report says not to stage the model and to raise `min_samples_leaf` above 2 or lower `max_depth` below 5. That run does not reopen the 2024–2025 report card.

## Architecture and Data Flow

Training path: raw CSV → schema checks → chronological split → causal features on the full series → year-blocked RF selection inside train (calibration window held out) → conformal quantile on last 24 training months → refit on all training feature rows → one-step test scoring → `data/eval/sales_forecast/`.

Evaluation path: read frozen settings from `metrics.json` → split → causal features on the training raw frame only → five expanding year folds → in-sample and validation MAE/RMSE → 2022–2023 side score → two-line learning curve and `data/eval/evaluation_report.md`. Isolated `uv` project under `scripts/sales_forecast/`. Does not call the FastAPI app.

## Important Files

- `scripts/train_sales_forecast.py`
- `scripts/eval_sales_forecast.py`
- `scripts/sales_forecast/sales_forecast/evaluation.py`
- `scripts/sales_forecast/`
- `tests/pipelines/test_sales_forecast_*.py`
- `data/raw/healthcore_sales.csv`
- `data/eval/evaluation_report.md`
- `data/eval/sales_forecast/cv_metrics.json`
- `data/eval/sales_forecast/learning_curve.png`
- `docs/sales-forecast/sales-forecast.md`

## Interfaces and Contracts

Target `revenue_usd`. Same-month `visits_count` and `avg_revenue_per_visit_usd` are excluded. Gini is ranking Gini; K2 is D’Agostino–Pearson on residuals; PSI is on `visits_count` train vs test.

The fit rule is fixed: overfitting when the average 2022–2023 ratio `(validation MAE - training MAE) / validation MAE` is at least 0.50. Primary metric is MAE in USD. Sample standard deviation uses `ddof=1`. Inside a validation year, one-step features may use earlier actual revenue. Duplicate months or a second region stop the evaluation.

## Decisions and Constraints

Game A (one-month-ahead). Report-card go/no-go with no dollar cutoff. Random Forest, not XGBoost. Do not invent US/UK rows. Do not add ML deps to the API. Do not retune during the fit evaluation. Do not use 2024–2025 to choose the fit label.

## Validation

`uv --directory scripts/sales_forecast run pytest` (37 passed on 2026-11-06). Training script produces `data/eval/sales_forecast/metrics.json`. Evaluation script produces the report, `cv_metrics.json`, and `learning_curve.png`.

## Maintenance Notes

Re-run the training script after feature or metric changes, then re-run the evaluation script so the frozen settings and the report stay paired. Do not tune on 2024–2025. A `metrics.json` whose hyperparameters differ from 100 / 5 / 2 stops the evaluation instead of searching. The feasibility phase guide lives in [`archive/2026-11-05-sales-forecast-model/`](../archive/2026-11-05-sales-forecast-model/). The evaluation handoff lives in [`archive/2026-11-07-regression-model-eval/`](../archive/2026-11-07-regression-model-eval/).
