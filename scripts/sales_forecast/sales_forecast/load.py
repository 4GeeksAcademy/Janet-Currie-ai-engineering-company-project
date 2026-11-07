"""Read-only load and schema checks for the HealthCore sales CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .constants import (
    EXPECTED_YEAR_COUNT,
    EXPECTED_YEARS,
    MONTHS_PER_YEAR,
    REGION_VALUE,
    REQUIRED_COLUMNS,
    TARGET_COLUMN,
    TIME_COLUMN,
)


class SalesDataError(ValueError):
    """The sales CSV does not match the HealthCore contract."""


def load_sales(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SalesDataError(f"Sales file not found: {path}")
    frame = pd.read_csv(path)
    return validate_sales(frame)


def validate_sales(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise SalesDataError(f"Missing required columns: {missing}")

    out = frame.copy()
    out[TIME_COLUMN] = pd.to_datetime(out[TIME_COLUMN], format="%Y-%m-%d", errors="coerce")
    if out[TIME_COLUMN].isna().any():
        bad = int(out[TIME_COLUMN].isna().sum())
        raise SalesDataError(f"{bad} row(s) have a missing or unparseable {TIME_COLUMN}")

    for column in (TARGET_COLUMN, "visits_count", "avg_revenue_per_visit_usd"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
        if out[column].isna().any():
            raise SalesDataError(f"{column} contains missing or non-numeric values")

    out["region"] = out["region"].astype(str)
    out = out.loc[out["region"] == REGION_VALUE].copy()
    if out.empty:
        raise SalesDataError(f"No rows with region={REGION_VALUE!r}")

    if (out[TARGET_COLUMN] <= 0).any():
        raise SalesDataError("All revenue_usd values must be positive")
    if (out["visits_count"] <= 0).any():
        raise SalesDataError("visits_count must be positive")

    out = out.sort_values(TIME_COLUMN).reset_index(drop=True)
    if out[TIME_COLUMN].duplicated().any():
        raise SalesDataError("Duplicate month timestamps at the consolidated grain")

    years = tuple(int(year) for year in out[TIME_COLUMN].dt.year.unique())
    if years != EXPECTED_YEARS:
        raise SalesDataError(
            f"Expected {EXPECTED_YEAR_COUNT} years {list(EXPECTED_YEARS)}, found {list(years)}"
        )

    months_per_year = out.groupby(out[TIME_COLUMN].dt.year).size()
    if (months_per_year != MONTHS_PER_YEAR).any():
        raise SalesDataError("Each year must contain 12 months with no gaps")

    expected_index = pd.date_range(
        out[TIME_COLUMN].min(),
        out[TIME_COLUMN].max(),
        freq="MS",
    )
    actual_index = pd.DatetimeIndex(out[TIME_COLUMN])
    missing_months = expected_index.difference(actual_index)
    if len(missing_months) > 0:
        raise SalesDataError(f"Missing months: {list(missing_months.astype(str))}")

    return out.reset_index(drop=True)
