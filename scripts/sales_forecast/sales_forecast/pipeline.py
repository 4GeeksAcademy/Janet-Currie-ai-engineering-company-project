"""End-to-end HealthCore sales-forecast training and evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .conclusion import report_card
from .constants import (
    CALIBRATION_MONTHS,
    EVAL_RELATIVE_DIR,
    FEATURE_COLUMNS,
    INTERVAL_COVERAGE,
    PROCESS_RELATIVE_DIR,
    RAW_RELATIVE_PATH,
    SEED,
    TARGET_COLUMN,
    TEST_YEARS,
    TIME_COLUMN,
    TRAIN_YEARS,
)
from .features import add_causal_features, drop_incomplete_feature_rows, feature_matrix
from .intervals import conformal_quantile, interval_diagnostics, prediction_interval
from .load import load_sales
from .metrics import evaluate_predictions, population_stability_index, regression_errors
from .model import fit_random_forest, select_random_forest
from .plot import plot_test_forecast
from .split import split_train_test


def _year_filter(frame: pd.DataFrame, years: tuple[int, ...]) -> pd.DataFrame:
    return frame.loc[frame[TIME_COLUMN].dt.year.isin(years)].copy().reset_index(drop=True)


def run_pipeline(repo_root: Path) -> dict[str, Any]:
    raw_path = repo_root / RAW_RELATIVE_PATH
    process_dir = repo_root / PROCESS_RELATIVE_DIR
    eval_dir = repo_root / EVAL_RELATIVE_DIR
    process_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    sales = load_sales(raw_path)
    train_raw, test_raw = split_train_test(sales)

    combined = pd.concat([train_raw, test_raw], ignore_index=True)
    featured = drop_incomplete_feature_rows(add_causal_features(combined))
    dropped_for_lags = len(combined) - len(featured)

    feat_train = _year_filter(featured, TRAIN_YEARS)
    feat_test = _year_filter(featured, TEST_YEARS)
    if feat_test.empty:
        raise ValueError("No test rows remain after lag-12 drop")

    if len(feat_train) <= CALIBRATION_MONTHS:
        raise ValueError("Not enough training rows to hold out a 24-month calibration window")
    selection = feat_train.iloc[:-CALIBRATION_MONTHS].copy()
    calibration = feat_train.iloc[-CALIBRATION_MONTHS:].copy()

    best_params, selection_mae = select_random_forest(selection)
    conformal_model = fit_random_forest(selection, best_params)
    calib_pred = conformal_model.predict(feature_matrix(calibration))
    quantile = conformal_quantile(
        calibration[TARGET_COLUMN].to_numpy(dtype=float),
        calib_pred,
        coverage=INTERVAL_COVERAGE,
    )

    final_model = fit_random_forest(feat_train, best_params)
    test_pred = final_model.predict(feature_matrix(feat_test))
    lower, upper = prediction_interval(test_pred, quantile)

    # revenue_lag_12 is ŷ_t = y_{t-12}, available in a one-month-ahead workflow.
    baseline_test = feat_test["revenue_lag_12"].to_numpy(dtype=float)
    actual_test = feat_test[TARGET_COLUMN].to_numpy(dtype=float)

    model_metrics = evaluate_predictions(actual_test, test_pred, prefix="model")
    baseline_metrics = evaluate_predictions(actual_test, baseline_test, prefix="baseline")
    psi_visits = population_stability_index(
        feat_train["visits_count"].to_numpy(dtype=float),
        feat_test["visits_count"].to_numpy(dtype=float),
    )
    interval_stats = interval_diagnostics(actual_test, lower, upper)

    residuals = actual_test - test_pred
    by_month = feat_test.assign(
        residual=residuals,
        abs_error=abs(residuals),
        predicted=test_pred,
    )
    jul_aug = by_month.loc[by_month[TIME_COLUMN].dt.month.isin((7, 8))]
    oct_dec = by_month.loc[by_month[TIME_COLUMN].dt.month.isin((10, 11, 12))]
    year_2024 = by_month.loc[by_month[TIME_COLUMN].dt.year == 2024]
    year_2025 = by_month.loc[by_month[TIME_COLUMN].dt.year == 2025]

    card = report_card(
        model_mae=float(model_metrics["model_mae"]),
        baseline_mae=float(baseline_metrics["baseline_mae"]),
        gini=float(model_metrics["model_gini"]),
        coverage=float(interval_stats["coverage"]),
    )

    predictions = feat_test[[TIME_COLUMN, TARGET_COLUMN, "visits_count"]].copy()
    predictions["predicted_revenue_usd"] = test_pred
    predictions["baseline_revenue_usd"] = baseline_test
    predictions["interval_lower_usd"] = lower
    predictions["interval_upper_usd"] = upper
    predictions["residual_usd"] = residuals
    predictions_path = eval_dir / "test_predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    features_path = process_dir / "features.csv"
    featured.to_csv(features_path, index=False)

    plot_path = eval_dir / "forecast_2024_2025.png"
    plot_test_forecast(
        feat_test,
        predicted=test_pred,
        lower=lower,
        upper=upper,
        path=plot_path,
    )

    payload: dict[str, Any] = {
        "business_question": (
            "Can HealthCore's historical monthly revenue predict next month "
            "well enough to support investing in an executive dashboard?"
        ),
        "horizon": "rolling_one_month_ahead",
        "target": TARGET_COLUMN,
        "source": str(RAW_RELATIVE_PATH),
        "n_source_rows": int(len(sales)),
        "n_feature_rows": int(len(featured)),
        "rows_dropped_for_lag12": int(dropped_for_lags),
        "train_years": list(TRAIN_YEARS),
        "test_years": list(TEST_YEARS),
        "n_train_feature_rows": int(len(feat_train)),
        "n_selection_rows": int(len(selection)),
        "n_calibration_rows": int(len(calibration)),
        "n_test_rows": int(len(feat_test)),
        "model_class": "RandomForestRegressor",
        "random_state": SEED,
        "hyperparameters": best_params,
        "selection_mae": selection_mae,
        "feature_columns": list(FEATURE_COLUMNS),
        "excluded_same_month_columns": [
            "visits_count",
            "avg_revenue_per_visit_usd",
            "region",
        ],
        "scaling": "not_applied_tree_splits_do_not_need_scaling",
        "interval": {
            "method": "split_conformal_absolute_residual_quantile",
            "nominal_coverage": INTERVAL_COVERAGE,
            "quantile_usd": quantile,
            **interval_stats,
            "point_model": "refit_on_all_training_feature_rows",
            "calibration": "last_24_training_months_after_hyperparameter_lock",
        },
        "metrics": {
            **model_metrics,
            **baseline_metrics,
            "psi_visits_count": psi_visits,
            "psi_note": (
                "PSI compares train vs test visits_count. US/UK mix PSI is not "
                "computable because the source file has only consolidated rows."
            ),
        },
        "diagnostics": {
            "mean_signed_error_usd": float(residuals.mean()),
            "jul_aug_mae_usd": float(jul_aug["abs_error"].mean()) if not jul_aug.empty else None,
            "oct_dec_mae_usd": float(oct_dec["abs_error"].mean()) if not oct_dec.empty else None,
            "year_2024_mae_usd": float(
                regression_errors(
                    year_2024[TARGET_COLUMN].to_numpy(dtype=float),
                    year_2024["predicted"].to_numpy(dtype=float),
                )["mae"]
            )
            if not year_2024.empty
            else None,
            "year_2025_mae_usd": float(
                regression_errors(
                    year_2025[TARGET_COLUMN].to_numpy(dtype=float),
                    year_2025["predicted"].to_numpy(dtype=float),
                )["mae"]
            )
            if not year_2025.empty
            else None,
        },
        "metric_definitions": {
            "mse": "sklearn.metrics.mean_squared_error, USD^2",
            "mae": "sklearn.metrics.mean_absolute_error, USD",
            "rmse": "sqrt(MSE), USD",
            "rmse_pct_of_mean": "RMSE / mean(test revenue) * 100",
            "r2": "sklearn.metrics.r2_score (supporting; not K2)",
            "gini": "normalized ranking Gini of predicted vs actual revenue",
            "k2": "scipy.stats.normaltest D'Agostino-Pearson K2 on residuals; closer to 0 is better",
            "psi": "population stability index of visits_count, bins from train only, empty bins clipped to 1e-4",
        },
        "report_card": card,
        "artifacts": {
            "features": str(features_path.relative_to(repo_root)),
            "predictions": str(predictions_path.relative_to(repo_root)),
            "plot": str(plot_path.relative_to(repo_root)),
        },
        "caveat": (
            "Performance on one two-year historical holdout is retrospective "
            "next-month skill under these conditions; it does not guarantee "
            "future performance under drift, policy changes, or shocks."
        ),
    }

    metrics_path = eval_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2) + "\n")
    payload["artifacts"]["metrics"] = str(metrics_path.relative_to(repo_root))
    metrics_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Report card: {card['decision']}")
    print(card["reason"])
    print(f"Wrote {metrics_path.relative_to(repo_root)}")
    print(f"Plot {plot_path.relative_to(repo_root)}")
    return payload
