"""Chronological folds, leakage, and the predeclared fit diagnosis."""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pandas as pd
import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "sales_forecast"
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from sales_forecast.constants import FEATURE_COLUMNS
from sales_forecast.evaluation import (
    EvaluationError,
    FoldMetrics,
    assert_evaluation_population,
    diagnose,
    diagnostic_folds,
    render_report,
    sample_std,
    training_feature_frame,
)
from sales_forecast.features import add_causal_features, drop_incomplete_feature_rows
from sales_forecast.split import split_train_test


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


def feature_frame(years=range(2016, 2021)) -> pd.DataFrame:
    raw = make_sales(years)
    return drop_incomplete_feature_rows(add_causal_features(raw))


def fold_metrics(
    year: int,
    *,
    train_mae: float,
    validation_mae: float,
    naive_validation_mae: float,
) -> FoldMetrics:
    return FoldMetrics(
        validation_year=year,
        n_train_rows=24 + (year - 2019) * 12,
        train_mae=train_mae,
        train_rmse=train_mae + 10.0,
        validation_mae=validation_mae,
        validation_rmse=validation_mae + 10.0,
        naive_validation_mae=naive_validation_mae,
        train_max_month=f"{year - 1}-12-01",
        validation_min_month=f"{year}-01-01",
        validation_max_month=f"{year}-12-01",
    )


def five_folds(
    *,
    train_mae: float,
    validation_mae: float,
    naive_validation_mae: float,
) -> list[FoldMetrics]:
    return [
        fold_metrics(
            year,
            train_mae=train_mae,
            validation_mae=validation_mae,
            naive_validation_mae=naive_validation_mae,
        )
        for year in (2019, 2020, 2021, 2022, 2023)
    ]


def test_folds_keep_chronological_order_and_move_forward() -> None:
    windows = diagnostic_folds(feature_frame())
    assert [window.validation_year for window in windows] == [2019, 2020]
    previous_validation_start = None
    previous_train_years: tuple[int, ...] | None = None
    for window in windows:
        train_times = pd.to_datetime(window.train["month"])
        validation_times = pd.to_datetime(window.validation["month"])
        assert train_times.is_monotonic_increasing
        assert validation_times.is_monotonic_increasing
        assert train_times.max() < validation_times.min()
        assert max(window.train_years) < window.validation_year
        if previous_validation_start is not None:
            assert validation_times.min() > previous_validation_start
            assert previous_train_years is not None
            assert window.validation_year not in previous_train_years
        previous_validation_start = validation_times.min()
        previous_train_years = window.train_years


def test_shuffled_rows_do_not_change_fold_order() -> None:
    ordered = diagnostic_folds(feature_frame())
    shuffled = diagnostic_folds(feature_frame().sample(frac=1.0, random_state=1))
    assert [window.validation_year for window in ordered] == [
        window.validation_year for window in shuffled
    ]
    for left, right in zip(ordered, shuffled):
        assert left.train["month"].max() == right.train["month"].max()
        assert left.validation["month"].min() == right.validation["month"].min()


def test_later_validation_year_is_absent_from_earlier_training() -> None:
    windows = diagnostic_folds(feature_frame())
    assert 2020 not in windows[0].train_years
    assert windows[0].validation_year in windows[1].train_years


def test_training_features_exclude_held_out_years() -> None:
    featured = training_feature_frame(make_sales())
    years = set(featured["month"].dt.year)
    assert years.isdisjoint({2024, 2025})
    assert years <= set(range(2016, 2024))
    assert [window.validation_year for window in diagnostic_folds(featured)] == [
        2019,
        2020,
        2021,
        2022,
        2023,
    ]


def test_duplicate_months_and_extra_regions_raise() -> None:
    duplicated = make_sales(years=range(2016, 2017))
    duplicated = pd.concat([duplicated, duplicated.iloc[[0]]], ignore_index=True)
    with pytest.raises(EvaluationError, match="Duplicate month"):
        assert_evaluation_population(duplicated)

    featured = feature_frame()
    extra = pd.concat([featured, featured.iloc[[0]]], ignore_index=True)
    with pytest.raises(EvaluationError, match="Duplicate month"):
        diagnostic_folds(extra)

    mixed = make_sales(years=range(2016, 2017))
    mixed.loc[0, "region"] = "uk"
    with pytest.raises(EvaluationError, match="only region"):
        assert_evaluation_population(mixed)


def test_train_only_features_match_the_training_slice_of_the_full_series() -> None:
    source = make_sales()
    train_raw, test_raw = split_train_test(source)
    test_raw = test_raw.copy()
    test_raw["revenue_usd"] = 1_000_000_000_000.0
    test_raw["visits_count"] = 1_000_000_000.0
    combined = pd.concat([train_raw, test_raw], ignore_index=True)
    full_features = drop_incomplete_feature_rows(add_causal_features(combined))
    train_features = drop_incomplete_feature_rows(add_causal_features(train_raw))
    full_train = full_features.loc[full_features["month"].dt.year < 2024]
    columns = ["month", "revenue_usd", *FEATURE_COLUMNS]
    pd.testing.assert_frame_equal(
        train_features.loc[:, columns].reset_index(drop=True),
        full_train.loc[:, columns].reset_index(drop=True),
    )


def test_lag_and_rolling_mean_use_only_earlier_revenue() -> None:
    revenues = [10.0, 20.0, 30.0, 40.0, 50.0]
    start = pd.Timestamp("2016-01-01")
    frame = pd.DataFrame(
        {
            "month": [start + pd.DateOffset(months=index) for index in range(len(revenues))],
            "revenue_usd": revenues,
            "visits_count": [100.0] * len(revenues),
            "avg_revenue_per_visit_usd": [10.0] * len(revenues),
            "region": ["consolidated"] * len(revenues),
        }
    )
    featured = add_causal_features(frame)
    april = featured.loc[featured["month"] == pd.Timestamp("2016-04-01")].iloc[0]
    may = featured.loc[featured["month"] == pd.Timestamp("2016-05-01")].iloc[0]
    assert april["revenue_lag_1"] == pytest.approx(30.0)
    assert april["revenue_roll_mean_3"] == pytest.approx((10.0 + 20.0 + 30.0) / 3.0)
    assert may["revenue_lag_1"] == pytest.approx(40.0)
    assert may["revenue_roll_mean_3"] == pytest.approx((20.0 + 30.0 + 40.0) / 3.0)
    assert pd.isna(featured.loc[0, "revenue_lag_1"])


def test_gap_of_one_half_is_overfitting() -> None:
    diagnosis = diagnose(
        five_folds(train_mae=50.0, validation_mae=100.0, naive_validation_mae=10.0)
    )
    assert diagnosis["label"] == "overfitting"
    assert diagnosis["late_gap_ratio"] == pytest.approx(0.5)
    assert diagnosis["display_label"] == "Overfitting"


def test_gap_just_below_one_half_and_weak_accuracy_is_underfitting() -> None:
    diagnosis = diagnose(
        five_folds(train_mae=50.01, validation_mae=100.0, naive_validation_mae=100.0)
    )
    assert diagnosis["late_gap_ratio"] < 0.5
    assert diagnosis["label"] == "underfitting"
    assert "revenue_lag_12" in diagnosis["next_action"]


def test_gap_just_below_one_half_and_better_than_naive_is_well_fitted() -> None:
    diagnosis = diagnose(
        five_folds(train_mae=50.01, validation_mae=80.0, naive_validation_mae=100.0)
    )
    assert diagnosis["late_gap_ratio"] < 0.5
    assert diagnosis["label"] == "reasonably_well_fitted"
    assert "staging review" in diagnosis["staging_sentence"].lower()


def test_validation_mae_equal_to_naive_is_underfitting() -> None:
    diagnosis = diagnose(
        five_folds(train_mae=90.0, validation_mae=100.0, naive_validation_mae=100.0)
    )
    assert diagnosis["label"] == "underfitting"


def test_diagnosis_requires_2022_and_2023() -> None:
    folds = five_folds(train_mae=50.0, validation_mae=100.0, naive_validation_mae=10.0)
    with pytest.raises(EvaluationError, match="2023"):
        diagnose(folds[:-1])


def test_sample_std_divides_by_four() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert sample_std(values) == pytest.approx(statistics.stdev(values))
    assert sample_std(values) == pytest.approx(2.5**0.5)


def test_report_names_the_diagnosis_and_keeps_holdout_years_out_of_the_folds() -> None:
    diagnosis = diagnose(
        five_folds(train_mae=50.0, validation_mae=100.0, naive_validation_mae=10.0)
    )
    folds = [
        {
            "validation_year": year,
            "n_train_rows": 24,
            "train_mae": 50.0,
            "train_rmse": 60.0,
            "validation_mae": 100.0,
            "validation_rmse": 120.0,
            "naive_validation_mae": 10.0,
        }
        for year in (2019, 2020, 2021, 2022, 2023)
    ]
    summary = {
        "train_mae": {"mean": 50.0, "sample_std": 0.0, "n": 5},
        "train_rmse": {"mean": 60.0, "sample_std": 0.0, "n": 5},
        "validation_mae": {"mean": 100.0, "sample_std": 1.5, "n": 5},
        "validation_rmse": {"mean": 120.0, "sample_std": 1.5, "n": 5},
        "naive_validation_mae": {"mean": 10.0, "sample_std": 0.0, "n": 5},
    }
    text = render_report(
        {
            "diagnosis": diagnosis,
            "summary": summary,
            "folds": folds,
            "side_score": {
                "train_end_year": 2021,
                "n_train_rows": 60,
                "n_scored_rows": 24,
                "mae": 90.0,
                "rmse": 95.0,
            },
            "held_out_test_years": [2024, 2025],
            "source": "data/raw/healthcore_sales.csv",
            "train_years": list(range(2016, 2024)),
            "n_train_feature_rows": 84,
            "feature_year_min": 2017,
            "feature_year_max": 2023,
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 5,
                "min_samples_leaf": 2,
            },
            "random_state": 42,
            "hyperparameters_source": "data/eval/sales_forecast/metrics.json",
            "feature_columns": list(FEATURE_COLUMNS),
            "validation_years": [2019, 2020, 2021, 2022, 2023],
            "selection_overlap_years": [2019, 2020, 2021],
            "learning_curve_interpretation": "Validation MAE fell from $100.00 to $100.00.",
            "learning_curve_relative_to_report": "sales_forecast/learning_curve.png",
            "artifacts": {
                "cv_metrics": "data/eval/sales_forecast/cv_metrics.json",
                "learning_curve": "data/eval/sales_forecast/learning_curve.png",
            },
        }
    )
    assert "Overfitting" in text
    assert "sample standard deviation" in text
    assert "$50.00 ± $0.00" in text
    assert "not cross-validation folds" in text
    fold_section = text.split("## Fold results", 1)[1].split("## Mean", 1)[0]
    assert "2024" not in fold_section
    assert "2025" not in fold_section
    assert "| 2019 |" in fold_section
    assert "| 2023 |" in fold_section
