# HealthCore sales forecast — feasibility results

Sandra asked whether historical monthly revenue can predict **coming months** well enough to justify an executive dashboard. This experiment answers that with a rolling **one-month-ahead** Random Forest on the supplied consolidated sales file. It is not a dashboard and not a 24-month forecast from December 2023.

Contracts: [`healthcore-BRIEFING.en.md`](../../memory-bank/archive/2026-11-05-sales-forecast-model/healthcore-BRIEFING.en.md), [`sales-forecast-model-context.md`](../../memory-bank/archive/2026-11-05-sales-forecast-model/sales-forecast-model-context.md). Plan: [`sales-forecast-implementation-plan.md`](sales-forecast-implementation-plan.md).

## How to run

From the repo root:

```bash
uv sync --directory scripts/sales_forecast --group dev
uv --directory scripts/sales_forecast run pytest
uv --directory scripts/sales_forecast run python ../train_sales_forecast.py
```

After the venv exists, `python3 scripts/train_sales_forecast.py` re-execs `scripts/sales_forecast/.venv`.

Do not install these packages into `services/api` or the stdlib incident analyzer.

## Data contract

| Item | Value |
|------|--------|
| Source | `data/raw/healthcore_sales.csv` (unmodified) |
| Grain | one consolidated network-month |
| Target | `revenue_usd` (USD) |
| Span | 2016-01 through 2025-12 (120 rows, no gaps) |
| Train | 2016–2023 (96 months; 84 remain after lag-12 drop) |
| Test | 2024–2025 (24 months) |
| Horizon | rolling one-month-ahead (Game A) |
| Seed | 42 |

Same-month `visits_count` and `avg_revenue_per_visit_usd` are **not** features. Together they almost reconstruct revenue (`revenue ≈ visits × avg`). `region` is constant (`consolidated`) and is dropped. Lagged visits are allowed.

The briefing’s 2–6% growth and 12–18% seasonality bands are interpretation aids. The CSV is used as-is; some years fall slightly outside those bands.

## Model

- Baseline: seasonal naive `ŷ_t = y_{t-12}` (same month last year).
- Features: month number, month sin/cos, time index, revenue lag 1 and 12, shifted rolling means 3 and 12, visits lag 1.
- Estimator: `RandomForestRegressor`. Trees do not need feature scaling.
- Selection: expanding-year MAE **inside** 2017–2021 (last 24 training months held out of hyperparameter search).
- Locked params: `n_estimators=100`, `max_depth=5`, `min_samples_leaf=2`, `random_state=42`.
- Point model: refit on all 84 training feature rows.
- Interval: 80% split-conformal quantile from the last 24 training months (`± $305,028`). Test coverage was not used to widen the band.

## Test-set metrics (2024–2025, n=24)

| Metric | Random Forest | Seasonal naive |
|--------|---------------|----------------|
| MAE (USD) | 163,235 | **161,558** |
| RMSE (USD) | 203,634 | **186,028** |
| RMSE / mean revenue | 6.05% | **5.53%** |
| MSE (USD²) | 4.147e10 | **3.461e10** |
| R² (supporting; not K2) | 0.672 | **0.727** |
| Ranking Gini | **0.918** | 0.914 |
| Residual K2 (closer to 0 is better) | **0.044** (p=0.978) | 0.450 (p=0.799) |

Mean test revenue is about **$3.37M**. MAE is the headline Finance number. MSE is reported in USD² as required; the percentage translation is **RMSE / mean revenue**, not MSE / mean.

**Gini** is normalized ranking Gini of predicted vs actual `revenue_usd` (no fake good/bad cutoff). High Gini means the model orders quiet vs busy months correctly.

**K2** is D’Agostino–Pearson K² (`scipy.stats.normaltest`) on residuals. Near 0 means leftovers look like ordinary noise. It is not R².

**PSI** of `visits_count` (train vs test, bins from train only) is **3.39**. That is a large level shift: visits grew over the decade, so the test distribution is not the training distribution. US/UK mix PSI cannot be computed — the file has only `consolidated` rows. No regional series was invented.

Interval empirical coverage is **79.2%** vs 80% nominal; mean width is about **$610k**.

Jul–Aug MAE is about $70k; Oct–Dec MAE is about $247k. 2025 MAE ($191k) is worse than 2024 ($136k). Mean signed error is a small over-forecast (~$14k).

## Why low MSE is not enough

The forest captures seasonality and ranks months well, and residuals look well-behaved. It still **does not beat last year’s same month** on MAE, RMSE, or R². A dashboard that merely plots “the model” would not outperform a one-line seasonal naive for next-month dollar error.

## Report card

**Unsupported** for dashboard investment on this holdout.

Rules: if model MAE ≥ seasonal-naive MAE, the answer is no. Gini and interval coverage both passed; they do not override a loss to the baseline.

This is retrospective next-month skill on one two-year holdout. It does not prove what would happen under a new clinic mix, policy change, or shock.

## Artifacts

- [`data/eval/sales_forecast/metrics.json`](../../data/eval/sales_forecast/metrics.json)
- [`data/eval/sales_forecast/test_predictions.csv`](../../data/eval/sales_forecast/test_predictions.csv)
- [`data/eval/sales_forecast/forecast_2024_2025.png`](../../data/eval/sales_forecast/forecast_2024_2025.png)
- [`data/process/sales_forecast/features.csv`](../../data/process/sales_forecast/features.csv)

## Tests

```bash
uv --directory scripts/sales_forecast run pytest
```

**23 passed** (2026-11-05): 8/2 split (including shuffled input and the real CSV), seasonal-naive lag-12, lag/rolling leakage, interval ordering, seed reproducibility, PSI empty bins, Gini ties, residual K2, report-card branches.
