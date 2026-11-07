"""Causal calendar, lag, and rolling features.

Same-month visits_count and avg_revenue_per_visit_usd are excluded because
they are contemporaneous with revenue (near identity leakage). Region is
constant in the supplied file.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import FEATURE_COLUMNS, TARGET_COLUMN, TIME_COLUMN


LEAKY_COLUMNS = ("visits_count", "avg_revenue_per_visit_usd", "region")


def add_causal_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add features for time t using only rows strictly before t."""
    if TIME_COLUMN not in frame.columns or TARGET_COLUMN not in frame.columns:
        raise ValueError("month and revenue_usd are required")
    out = frame.copy()
    out[TIME_COLUMN] = pd.to_datetime(out[TIME_COLUMN])
    out = out.sort_values(TIME_COLUMN).reset_index(drop=True)

    month_num = out[TIME_COLUMN].dt.month.astype(float)
    out["month_num"] = month_num
    out["month_sin"] = np.sin(2.0 * np.pi * month_num / 12.0)
    out["month_cos"] = np.cos(2.0 * np.pi * month_num / 12.0)
    start = out[TIME_COLUMN].min()
    out["time_index"] = (
        (out[TIME_COLUMN].dt.year - start.year) * 12
        + (out[TIME_COLUMN].dt.month - start.month)
    ).astype(float)

    revenue = out[TARGET_COLUMN].astype(float)
    visits = out["visits_count"].astype(float)
    out["revenue_lag_1"] = revenue.shift(1)
    out["revenue_lag_12"] = revenue.shift(12)
    out["revenue_roll_mean_3"] = revenue.shift(1).rolling(window=3, min_periods=3).mean()
    out["revenue_roll_mean_12"] = revenue.shift(1).rolling(window=12, min_periods=12).mean()
    out["visits_lag_1"] = visits.shift(1)
    return out


def drop_incomplete_feature_rows(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    return frame.dropna(subset=list(FEATURE_COLUMNS)).reset_index(drop=True)


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    leak = [column for column in LEAKY_COLUMNS if column in FEATURE_COLUMNS]
    if leak:
        raise ValueError(f"Leaky columns listed as features: {leak}")
    return frame.loc[:, list(FEATURE_COLUMNS)].astype(float)
