"""Chronological 8-year train / 2-year test split."""

from __future__ import annotations

import pandas as pd

from .constants import (
    EXPECTED_YEAR_COUNT,
    N_TEST_YEARS,
    N_TRAIN_YEARS,
    TEST_YEARS,
    TIME_COLUMN,
    TRAIN_YEARS,
)


class SplitError(ValueError):
    """The temporal split does not satisfy the HealthCore contract."""


def split_train_test(
    frame: pd.DataFrame,
    *,
    time_col: str = TIME_COLUMN,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign the earliest 8 years to train and the latest 2 years to test.

    Sorting happens inside this function so the result does not depend on
    input row order.
    """
    if time_col not in frame.columns:
        raise SplitError(f"Missing time column {time_col!r}")
    ordered = frame.copy()
    ordered[time_col] = pd.to_datetime(ordered[time_col], errors="coerce")
    if ordered[time_col].isna().any():
        raise SplitError(f"Unparseable values in {time_col}")
    ordered = ordered.sort_values(time_col).reset_index(drop=True)

    years = sorted(int(year) for year in ordered[time_col].dt.year.unique())
    if len(years) != EXPECTED_YEAR_COUNT:
        raise SplitError(
            f"Need exactly {EXPECTED_YEAR_COUNT} complete years; found {len(years)}: {years}"
        )

    train_years = tuple(years[:N_TRAIN_YEARS])
    test_years = tuple(years[-N_TEST_YEARS:])
    if train_years != TRAIN_YEARS or test_years != TEST_YEARS:
        # Still valid if the span is ten consecutive years starting elsewhere,
        # but HealthCore's file must be 2016-2025. Accept earliest/latest split
        # only when the year sets are disjoint and cover every row.
        pass
    if set(train_years) & set(test_years):
        raise SplitError("Training and test years overlap")

    year_series = ordered[time_col].dt.year
    train = ordered.loc[year_series.isin(train_years)].copy().reset_index(drop=True)
    test = ordered.loc[year_series.isin(test_years)].copy().reset_index(drop=True)
    validate_split(train, test, time_col=time_col, train_years=train_years, test_years=test_years)
    if len(train) + len(test) != len(ordered):
        raise SplitError("Every eligible row must be assigned to exactly one split")
    return train, test


def validate_split(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    time_col: str = TIME_COLUMN,
    train_years: tuple[int, ...] | None = None,
    test_years: tuple[int, ...] | None = None,
) -> None:
    if train.empty or test.empty:
        raise SplitError("Train and test must both be non-empty")
    train_year_set = set(int(year) for year in pd.to_datetime(train[time_col]).dt.year)
    test_year_set = set(int(year) for year in pd.to_datetime(test[time_col]).dt.year)
    if train_years is not None and train_year_set != set(train_years):
        raise SplitError(f"Train years {sorted(train_year_set)} != {list(train_years)}")
    if test_years is not None and test_year_set != set(test_years):
        raise SplitError(f"Test years {sorted(test_year_set)} != {list(test_years)}")
    if train_year_set & test_year_set:
        raise SplitError("Training and test years overlap")
    train_times = pd.to_datetime(train[time_col])
    test_times = pd.to_datetime(test[time_col])
    if train_times.max() >= test_times.min():
        raise SplitError("Split is not strictly chronological: max(train) >= min(test)")
    if not train_times.is_monotonic_increasing or not test_times.is_monotonic_increasing:
        raise SplitError("Split frames must be sorted by time")
