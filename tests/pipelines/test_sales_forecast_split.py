"""8-year / 2-year temporal split contract for the sales forecast."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "sales_forecast"
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from sales_forecast.load import SalesDataError, load_sales, validate_sales
from sales_forecast.split import SplitError, split_train_test, validate_split

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_sales(years=range(2016, 2026), *, shuffle: bool = False) -> pd.DataFrame:
    rows = []
    for year in years:
        for month in range(1, 13):
            rows.append(
                {
                    "month": f"{year}-{month:02d}-01",
                    "revenue_usd": float(1_000_000 + year * 1000 + month),
                    "visits_count": 10_000 + month,
                    "avg_revenue_per_visit_usd": 170.0,
                    "region": "consolidated",
                }
            )
    frame = pd.DataFrame(rows)
    if shuffle:
        frame = frame.sample(frac=1.0, random_state=0).reset_index(drop=True)
    return frame


def test_earliest_eight_years_train_latest_two_test() -> None:
    train, test = split_train_test(make_sales())
    assert set(train["month"].dt.year) == set(range(2016, 2024))
    assert set(test["month"].dt.year) == {2024, 2025}
    assert len(train) == 96
    assert len(test) == 24


def test_split_is_independent_of_row_order() -> None:
    ordered = make_sales(shuffle=False)
    shuffled = make_sales(shuffle=True)
    train_a, test_a = split_train_test(ordered)
    train_b, test_b = split_train_test(shuffled)
    pd.testing.assert_frame_equal(train_a.reset_index(drop=True), train_b.reset_index(drop=True))
    pd.testing.assert_frame_equal(test_a.reset_index(drop=True), test_b.reset_index(drop=True))


def test_train_and_test_years_do_not_overlap() -> None:
    train, test = split_train_test(make_sales())
    assert set(train["month"].dt.year).isdisjoint(set(test["month"].dt.year))
    assert train["month"].max() < test["month"].min()
    validate_split(train, test, train_years=tuple(range(2016, 2024)), test_years=(2024, 2025))


def test_every_row_assigned_once() -> None:
    source = make_sales()
    train, test = split_train_test(source)
    combined = pd.concat([train, test], ignore_index=True)
    assert len(combined) == len(source)
    assert combined["month"].nunique() == len(source)


def test_insufficient_years_fail() -> None:
    with pytest.raises(SplitError, match="exactly 10"):
        split_train_test(make_sales(years=range(2016, 2023)))


def test_malformed_month_fails_validation() -> None:
    frame = make_sales()
    frame.loc[0, "month"] = "not-a-date"
    with pytest.raises(SalesDataError, match="unparseable"):
        validate_sales(frame)


def test_real_healthcore_csv_split() -> None:
    path = REPO_ROOT / "data" / "raw" / "healthcore_sales.csv"
    sales = load_sales(path)
    train, test = split_train_test(sales)
    assert list(train["month"].dt.year.unique()) == list(range(2016, 2024))
    assert list(test["month"].dt.year.unique()) == [2024, 2025]
    assert train["month"].max() < test["month"].min()
    assert len(train) + len(test) == 120
