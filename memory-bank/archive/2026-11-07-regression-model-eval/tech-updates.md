# Tech updates — regression model evaluation

Closed 2026-11-07. No new packages.

- Evaluation lives in the existing `scripts/sales_forecast` uv project. Pandas, scikit-learn, and matplotlib were already installed.
- Folds reuse `expanding_year_folds`. Validation years are 2019–2023. Features are built from the training raw frame only.
- Frozen settings are read from `data/eval/sales_forecast/metrics.json`: 100 trees, `max_depth` 5, `min_samples_leaf` 2, seed 42.
- Primary metric is MAE in USD. Spread is the sample standard deviation (`statistics.stdev`, `ddof=1`).
- Fit rule: overfitting when the average 2022–2023 gap ratio is at least 0.50. The 2026-11-06 run produced 0.74, so the diagnosis is overfitting.
- 2024–2025 are not scored. The learning curve is two MAE lines and has no shaded band.
