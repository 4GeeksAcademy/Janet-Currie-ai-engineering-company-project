"""Causal feature and interval contract tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "sales_forecast"
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from sales_forecast.baseline import seasonal_naive_predictions
from sales_forecast.constants import FEATURE_COLUMNS, SEED
from sales_forecast.features import add_causal_features, drop_incomplete_feature_rows, feature_matrix
from sales_forecast.intervals import conformal_quantile, prediction_interval
from sales_forecast.model import fit_random_forest, make_regressor


def _series(revenues: list[float]) -> pd.DataFrame:
    start = pd.Timestamp("2016-01-01")
    months = [start + pd.DateOffset(months=index) for index in range(len(revenues))]
    return pd.DataFrame(
        {
            "month": months,
            "revenue_usd": revenues,
            "visits_count": [100 + index for index in range(len(revenues))],
            "avg_revenue_per_visit_usd": [10.0] * len(revenues),
            "region": ["consolidated"] * len(revenues),
        }
    )


def test_seasonal_naive_is_same_month_last_year() -> None:
    frame = _series([float(index) for index in range(15)])
    preds = seasonal_naive_predictions(frame)
    assert pd.isna(preds.iloc[11])
    assert preds.iloc[12] == pytest.approx(frame["revenue_usd"].iloc[0])


def test_lag_and_rolling_use_only_prior_rows() -> None:
    revenues = [10.0, 20.0, 30.0, 40.0, 50.0]
    featured = add_causal_features(_series(revenues))
    # First complete roll-3 row is index 3 (2016-04): mean of Jan-Mar = 20.
    assert featured.loc[3, "revenue_lag_1"] == pytest.approx(30.0)
    assert featured.loc[3, "revenue_roll_mean_3"] == pytest.approx(20.0)
    assert featured.loc[4, "revenue_roll_mean_3"] == pytest.approx(30.0)


def test_lag12_at_year_boundary() -> None:
    revenues = [float(index) for index in range(24)]
    featured = add_causal_features(_series(revenues))
    jan_next = featured.loc[featured["month"] == pd.Timestamp("2017-01-01")].iloc[0]
    dec_first = featured.loc[featured["month"] == pd.Timestamp("2016-12-01")].iloc[0]
    assert jan_next["revenue_lag_1"] == pytest.approx(dec_first["revenue_usd"])
    assert jan_next["revenue_lag_12"] == pytest.approx(revenues[0])


def test_incomplete_lags_are_dropped() -> None:
    revenues = [float(index) for index in range(15)]
    featured = drop_incomplete_feature_rows(add_causal_features(_series(revenues)))
    assert featured["revenue_lag_12"].notna().all()
    assert len(featured) == 3  # months 13-15 after dropping first 12


def test_feature_matrix_excludes_leaky_columns() -> None:
    featured = add_causal_features(_series([float(index) for index in range(14)]))
    matrix = feature_matrix(drop_incomplete_feature_rows(featured))
    assert list(matrix.columns) == list(FEATURE_COLUMNS)
    assert "visits_count" not in matrix.columns
    assert "avg_revenue_per_visit_usd" not in matrix.columns
    assert "revenue_usd" not in matrix.columns


def test_interval_ordering() -> None:
    point = np.array([10.0, 20.0, 30.0])
    lower, upper = prediction_interval(point, 2.5)
    assert np.all(lower <= point)
    assert np.all(point <= upper)


def test_conformal_quantile_is_non_negative() -> None:
    actual = np.array([10.0, 12.0, 14.0, 16.0])
    predicted = np.array([11.0, 11.0, 15.0, 20.0])
    quantile = conformal_quantile(actual, predicted, coverage=0.8)
    assert quantile >= 0


def test_random_forest_seed_reproducible() -> None:
    frame = drop_incomplete_feature_rows(
        add_causal_features(_series([100.0 + i * 3 for i in range(36)]))
    )
    params = {"n_estimators": 20, "max_depth": 3, "min_samples_leaf": 2}
    first = fit_random_forest(frame, params).predict(feature_matrix(frame))
    second = make_regressor(params)
    second.set_params(random_state=SEED)
    second.fit(feature_matrix(frame), frame["revenue_usd"])
    np.testing.assert_allclose(first, second.predict(feature_matrix(frame)))
