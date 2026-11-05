# HealthCore sales forecast

Isolated `uv` environment for the monthly revenue feasibility model. Entry point is [`../train_sales_forecast.py`](../train_sales_forecast.py).

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
```

Operator write-up: [`docs/sales-forecast/sales-forecast.md`](../../docs/sales-forecast/sales-forecast.md).
