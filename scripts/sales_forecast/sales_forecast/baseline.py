"""Seasonal-naive baseline: same month last year."""

from __future__ import annotations

import pandas as pd

from .constants import TARGET_COLUMN, TIME_COLUMN


def seasonal_naive_predictions(frame: pd.DataFrame) -> pd.Series:
    """Return ŷ_t = y_{t-12} aligned to frame's index.

    Uses actual observed revenue from 12 months earlier, which is available
    in a rolling one-month-ahead workflow.
    """
    ordered = frame.sort_values(TIME_COLUMN)
    lagged = ordered[TARGET_COLUMN].shift(12)
    return lagged.reindex(frame.index)
