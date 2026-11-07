# Tech updates — Sales forecast model

- Isolated uv project: [`scripts/sales_forecast/`](../../../scripts/sales_forecast/). Entry: [`scripts/train_sales_forecast.py`](../../../scripts/train_sales_forecast.py). Do not add sklearn to the API.
- Split: train 2016–2023 / test 2024–2025. Rolling one-month-ahead (Game A). Seed 42.
- Features: calendar month + sin/cos, time index, revenue lag 1 and 12, shifted rolling means 3 and 12, visits lag 1. Same-month `visits_count` and `avg_revenue_per_visit_usd` excluded.
- Model: `RandomForestRegressor` (`n_estimators=100`, `max_depth=5`, `min_samples_leaf=2`). Seasonal-naive baseline `ŷ_t = y_{t-12}`.
- Interval: 80% split conformal on last 24 training months. Test coverage 79.2%.
- Metrics on 24 test months: RF MAE $163,235 vs naive $161,558 → report card **unsupported**. Gini 0.918; K2 0.044; PSI(`visits_count`) 3.39.
- Tests: `tests/pipelines/test_sales_forecast_*.py` — **23 passed**.
- Artifacts: `data/eval/sales_forecast/` and `data/process/sales_forecast/`.
- Durable notes: [`implementation-memory/sales-forecast.md`](../../implementation-memory/sales-forecast.md).
