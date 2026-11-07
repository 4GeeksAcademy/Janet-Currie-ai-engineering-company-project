"""Shared contract for the HealthCore sales-forecast experiment."""

from __future__ import annotations

from pathlib import Path

SEED = 42
RAW_RELATIVE_PATH = Path("data/raw/healthcore_sales.csv")
PROCESS_RELATIVE_DIR = Path("data/process/sales_forecast")
EVAL_RELATIVE_DIR = Path("data/eval/sales_forecast")

REQUIRED_COLUMNS = (
    "month",
    "revenue_usd",
    "visits_count",
    "avg_revenue_per_visit_usd",
    "region",
)
TARGET_COLUMN = "revenue_usd"
TIME_COLUMN = "month"
REGION_VALUE = "consolidated"

EXPECTED_YEARS = tuple(range(2016, 2026))
TRAIN_YEARS = tuple(range(2016, 2024))
TEST_YEARS = (2024, 2025)
N_TRAIN_YEARS = 8
N_TEST_YEARS = 2
EXPECTED_YEAR_COUNT = 10
MONTHS_PER_YEAR = 12

INTERVAL_COVERAGE = 0.80
CALIBRATION_MONTHS = 24
PSI_BINS = 10
PSI_EPSILON = 1e-4

FEATURE_COLUMNS = (
    "month_num",
    "month_sin",
    "month_cos",
    "time_index",
    "revenue_lag_1",
    "revenue_lag_12",
    "revenue_roll_mean_3",
    "revenue_roll_mean_12",
    "visits_lag_1",
)

PARAM_GRID = tuple(
    {
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "min_samples_leaf": min_samples_leaf,
    }
    for n_estimators in (100, 200)
    for max_depth in (3, 5, 8)
    for min_samples_leaf in (2, 4)
)
