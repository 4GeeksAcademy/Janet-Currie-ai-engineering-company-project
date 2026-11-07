"""Training-period evaluation of the frozen HealthCore sales forecast.

The 2024–2025 holdout is split off and never scored. Hyperparameters are read
from the existing metrics file and are not searched again.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .constants import (
    CALIBRATION_MONTHS,
    EVAL_RELATIVE_DIR,
    FEATURE_COLUMNS,
    RAW_RELATIVE_PATH,
    REGION_VALUE,
    SEED,
    TARGET_COLUMN,
    TEST_YEARS,
    TIME_COLUMN,
    TRAIN_YEARS,
)
from .features import add_causal_features, drop_incomplete_feature_rows, feature_matrix
from .load import load_sales
from .metrics import regression_errors
from .model import expanding_year_folds, fit_random_forest
from .split import split_train_test


LOCKED_HYPERPARAMETERS = {
    "n_estimators": 100,
    "max_depth": 5,
    "min_samples_leaf": 2,
}
EXPECTED_VALIDATION_YEARS = (2019, 2020, 2021, 2022, 2023)
SELECTION_OVERLAP_YEARS = (2019, 2020, 2021)
LATE_VALIDATION_YEARS = (2022, 2023)
OVERFIT_LATE_GAP = 0.5
REPORT_RELATIVE_PATH = Path("data/eval/evaluation_report.md")
LEARNING_CURVE_NAME = "learning_curve.png"
CV_METRICS_NAME = "cv_metrics.json"


class EvaluationError(ValueError):
    """The regression evaluation cannot be completed under the locked contract."""


@dataclass(frozen=True)
class FoldWindow:
    """One expanding-year training window and the validation year that follows it."""

    validation_year: int
    train_years: tuple[int, ...]
    train: pd.DataFrame
    validation: pd.DataFrame


@dataclass(frozen=True)
class FoldMetrics:
    """MAE and RMSE for one validation year, in USD."""

    validation_year: int
    n_train_rows: int
    train_mae: float
    train_rmse: float
    validation_mae: float
    validation_rmse: float
    naive_validation_mae: float
    train_max_month: str
    validation_min_month: str
    validation_max_month: str


def assert_evaluation_population(frame: pd.DataFrame) -> None:
    """Require one consolidated row per month.

    Extra regions are an error. The sales loader drops them, so this check
    has to run on the raw frame first.
    """
    if TIME_COLUMN not in frame.columns or "region" not in frame.columns:
        raise EvaluationError(f"{TIME_COLUMN!r} and 'region' are required")
    regions = set(frame["region"].astype(str))
    if regions != {REGION_VALUE}:
        raise EvaluationError(
            f"Expected only region {REGION_VALUE!r}; found {sorted(regions)}"
        )
    months = pd.to_datetime(frame[TIME_COLUMN], errors="coerce")
    if months.isna().any():
        raise EvaluationError(f"{TIME_COLUMN} contains missing or unparseable values")
    if months.duplicated().any():
        raise EvaluationError("Duplicate month timestamps at the consolidated grain")


def load_frozen_hyperparameters(path: Path) -> dict[str, int]:
    """Read the already chosen forest settings. Refuse a different forest."""
    if not path.exists():
        raise EvaluationError(f"Frozen metrics file not found: {path}")
    payload = json.loads(path.read_text())
    raw = payload.get("hyperparameters")
    if not isinstance(raw, dict):
        raise EvaluationError("metrics.json is missing an object named hyperparameters")
    missing = [key for key in LOCKED_HYPERPARAMETERS if key not in raw]
    if missing:
        raise EvaluationError(f"metrics.json hyperparameters missing {missing}")
    found = {key: int(raw[key]) for key in LOCKED_HYPERPARAMETERS}
    if found != LOCKED_HYPERPARAMETERS:
        raise EvaluationError(
            f"Frozen hyperparameters {found} differ from {LOCKED_HYPERPARAMETERS}. "
            "Refusing to search again."
        )
    return found


def training_feature_frame(sales: pd.DataFrame) -> pd.DataFrame:
    """Causal features for the training years only.

    The held-out test split is created and then discarded so its revenue cannot
    enter lag or rolling features.
    """
    train_raw, test_raw = split_train_test(sales)
    if test_raw.empty:
        raise EvaluationError("Held-out test split is empty")
    featured = drop_incomplete_feature_rows(add_causal_features(train_raw))
    if featured.empty:
        raise EvaluationError("No training rows remain after the lag warmup")
    years = {int(year) for year in featured[TIME_COLUMN].dt.year}
    if years & set(TEST_YEARS):
        raise EvaluationError("Training feature frame includes held-out test years")
    if not years <= set(TRAIN_YEARS):
        raise EvaluationError(
            f"Training feature years {sorted(years)} are outside {list(TRAIN_YEARS)}"
        )
    return featured


def diagnostic_folds(frame: pd.DataFrame) -> list[FoldWindow]:
    """Expanding year folds with an explicit chronological contract."""
    if TIME_COLUMN not in frame.columns:
        raise EvaluationError(f"{TIME_COLUMN!r} is required")
    ordered = frame.copy()
    ordered[TIME_COLUMN] = pd.to_datetime(ordered[TIME_COLUMN], errors="coerce")
    if ordered[TIME_COLUMN].isna().any():
        raise EvaluationError(f"{TIME_COLUMN} contains missing or unparseable values")
    ordered = ordered.sort_values(TIME_COLUMN).reset_index(drop=True)
    if ordered[TIME_COLUMN].duplicated().any():
        raise EvaluationError("Duplicate month timestamps at the consolidated grain")

    windows: list[FoldWindow] = []
    for train, validation in expanding_year_folds(ordered):
        train_times = pd.to_datetime(train[TIME_COLUMN])
        validation_times = pd.to_datetime(validation[TIME_COLUMN])
        if not bool(train_times.is_monotonic_increasing) or not bool(
            validation_times.is_monotonic_increasing
        ):
            raise EvaluationError("Fold timestamps are not in chronological order")
        if train_times.max() >= validation_times.min():
            raise EvaluationError(
                "Fold is not strictly chronological: max(train) >= min(validation)"
            )
        train_years = tuple(sorted({int(year) for year in train_times.dt.year}))
        validation_years = tuple(sorted({int(year) for year in validation_times.dt.year}))
        if len(validation_years) != 1:
            raise EvaluationError(f"Validation window spans years {list(validation_years)}")
        validation_year = validation_years[0]
        if any(year >= validation_year for year in train_years):
            raise EvaluationError(
                f"Training years {list(train_years)} are not strictly before {validation_year}"
            )
        windows.append(
            FoldWindow(
                validation_year=validation_year,
                train_years=train_years,
                train=train.reset_index(drop=True),
                validation=validation.reset_index(drop=True),
            )
        )
    if not windows:
        raise EvaluationError("Not enough years for an expanding validation fold")
    _assert_expanding_order(windows)
    return windows


def assert_healthcore_folds(windows: Sequence[FoldWindow]) -> None:
    years = tuple(window.validation_year for window in windows)
    if years != EXPECTED_VALIDATION_YEARS:
        raise EvaluationError(
            "Expected validation years "
            f"{list(EXPECTED_VALIDATION_YEARS)}, found {list(years)}"
        )


def score_fold(window: FoldWindow, params: Mapping[str, int]) -> FoldMetrics:
    """Fit the frozen forest and score the months it just saw, then the next year."""
    model = fit_random_forest(window.train, params)
    train_predicted = model.predict(feature_matrix(window.train))
    validation_predicted = model.predict(feature_matrix(window.validation))
    train_actual = window.train[TARGET_COLUMN].to_numpy(dtype=float)
    validation_actual = window.validation[TARGET_COLUMN].to_numpy(dtype=float)
    train_errors = regression_errors(train_actual, train_predicted)
    validation_errors = regression_errors(validation_actual, validation_predicted)
    naive = window.validation["revenue_lag_12"].to_numpy(dtype=float)
    if np.isnan(naive).any():
        raise EvaluationError(
            f"Seasonal-naive lag is missing in validation year {window.validation_year}"
        )
    naive_errors = regression_errors(validation_actual, naive)
    train_times = pd.to_datetime(window.train[TIME_COLUMN])
    validation_times = pd.to_datetime(window.validation[TIME_COLUMN])
    return FoldMetrics(
        validation_year=window.validation_year,
        n_train_rows=int(len(window.train)),
        train_mae=train_errors["mae"],
        train_rmse=train_errors["rmse"],
        validation_mae=validation_errors["mae"],
        validation_rmse=validation_errors["rmse"],
        naive_validation_mae=naive_errors["mae"],
        train_max_month=_iso_month(train_times.max()),
        validation_min_month=_iso_month(validation_times.min()),
        validation_max_month=_iso_month(validation_times.max()),
    )


def sample_std(values: Sequence[float]) -> float:
    """Sample standard deviation, dividing by n - 1."""
    if len(values) < 2:
        raise EvaluationError("Sample standard deviation needs at least two values")
    return float(statistics.stdev(values))


def summarize_folds(folds: Sequence[FoldMetrics]) -> dict[str, Any]:
    if len(folds) < 2:
        raise EvaluationError("Summaries need at least two folds")
    return {
        "train_mae": _metric_summary([fold.train_mae for fold in folds]),
        "train_rmse": _metric_summary([fold.train_rmse for fold in folds]),
        "validation_mae": _metric_summary([fold.validation_mae for fold in folds]),
        "validation_rmse": _metric_summary([fold.validation_rmse for fold in folds]),
        "naive_validation_mae": _metric_summary([fold.naive_validation_mae for fold in folds]),
        "primary_metric": "mae_usd",
        "std_method": "sample_ddof_1",
    }


def diagnose(folds: Sequence[FoldMetrics]) -> dict[str, Any]:
    """Classify fit from the predeclared 2022–2023 gap rule."""
    years = [fold.validation_year for fold in folds]
    if len(years) != len(set(years)):
        raise EvaluationError("Duplicate validation year in diagnosis input")
    by_year = {fold.validation_year: fold for fold in folds}
    missing = [year for year in LATE_VALIDATION_YEARS if year not in by_year]
    if missing:
        raise EvaluationError(
            f"Diagnosis needs validation years {list(LATE_VALIDATION_YEARS)}; missing {missing}"
        )
    late_gaps: list[float] = []
    late_gap_dollars: list[float] = []
    for year in LATE_VALIDATION_YEARS:
        fold = by_year[year]
        if fold.validation_mae <= 0:
            raise EvaluationError(f"Validation MAE for {year} must be positive")
        late_gaps.append((fold.validation_mae - fold.train_mae) / fold.validation_mae)
        late_gap_dollars.append(fold.validation_mae - fold.train_mae)
    late_gap = float(statistics.fmean(late_gaps))
    late_gap_usd = float(statistics.fmean(late_gap_dollars))
    mean_validation = float(statistics.fmean(fold.validation_mae for fold in folds))
    mean_naive = float(statistics.fmean(fold.naive_validation_mae for fold in folds))
    validation_std = sample_std([fold.validation_mae for fold in folds])
    rule = (
        "Overfitting when the average 2022–2023 gap ratio "
        f"(validation MAE - training MAE) / validation MAE is at least {OVERFIT_LATE_GAP:.2f}. "
        "Underfitting when that ratio is below "
        f"{OVERFIT_LATE_GAP:.2f} and mean validation MAE is at least the mean "
        "seasonal-naive validation MAE. Reasonably well fitted when that ratio is below "
        f"{OVERFIT_LATE_GAP:.2f} and mean validation MAE is below the seasonal-naive mean."
    )
    if late_gap >= OVERFIT_LATE_GAP:
        label = "overfitting"
        display = "Overfitting"
        staging = "Do not stage this model. The next change is stronger regularization."
        action = (
            "Raise min_samples_leaf above 2 or lower max_depth below 5 on the frozen "
            f"RandomForestRegressor (n_estimators=100, max_depth=5, min_samples_leaf=2, "
            f"random_state={SEED}). The 2022 and 2023 folds still show an average gap ratio "
            f"of {late_gap:.2f}: validation MAE exceeds in-sample training MAE by "
            f"{_usd(late_gap_usd)} on average. Adding trees or depth would not be the next change."
        )
    elif mean_validation >= mean_naive:
        label = "underfitting"
        display = "Underfitting"
        staging = "Do not stage this model. The next change is the feature family."
        action = (
            "Revise the lag and rolling feature family (revenue_lag_1, revenue_lag_12, "
            "revenue_roll_mean_3, revenue_roll_mean_12, visits_lag_1) before adding trees. "
            f"Mean validation MAE is {_usd(mean_validation)}, which is not below the "
            f"seasonal-naive mean of {_usd(mean_naive)}. The 2022–2023 gap ratio is "
            f"{late_gap:.2f}, already under {OVERFIT_LATE_GAP:.2f}, so the training and "
            "validation errors have come together while remaining no better than "
            "same-month-last-year."
        )
    else:
        label = "reasonably_well_fitted"
        display = "Reasonably well fitted"
        staging = (
            "Recommend a staging review. State the limitations below beside that recommendation."
        )
        action = (
            "Recommend a staging review. Mean validation MAE is "
            f"{_usd(mean_validation)}, below the seasonal-naive mean of {_usd(mean_naive)}, "
            f"and the 2022–2023 gap ratio is {late_gap:.2f} (under {OVERFIT_LATE_GAP:.2f}). "
            f"Monitor the sample standard deviation of validation MAE, {_usd(validation_std)}. "
            "The 2019–2021 folds overlap the months that chose these settings, so the five-fold "
            "mean can look rosy. CONTEXT.md does not say whether over-predicting or "
            "under-predicting revenue costs more."
        )
    return {
        "label": label,
        "display_label": display,
        "late_gap_ratio": late_gap,
        "late_gap_usd": late_gap_usd,
        "mean_validation_mae": mean_validation,
        "mean_naive_validation_mae": mean_naive,
        "validation_mae_sample_std": validation_std,
        "rule": rule,
        "next_action": action,
        "staging_sentence": staging,
    }


def score_side_window(featured: pd.DataFrame, params: Mapping[str, int]) -> dict[str, Any]:
    """Score 2022–2023 from a fit that ended in 2021. This is not a sixth fold."""
    if len(featured) <= CALIBRATION_MONTHS:
        raise EvaluationError("Not enough training rows for the 24-month side score")
    selection = featured.iloc[:-CALIBRATION_MONTHS].copy()
    calibration = featured.iloc[-CALIBRATION_MONTHS:].copy()
    scored_years = tuple(sorted({int(year) for year in calibration[TIME_COLUMN].dt.year}))
    if scored_years != LATE_VALIDATION_YEARS:
        raise EvaluationError(
            f"Side-score years {list(scored_years)} are not {list(LATE_VALIDATION_YEARS)}"
        )
    train_end_year = int(selection[TIME_COLUMN].dt.year.max())
    if train_end_year >= LATE_VALIDATION_YEARS[0]:
        raise EvaluationError("Side-score training window includes 2022 or later")
    model = fit_random_forest(selection, params)
    predicted = model.predict(feature_matrix(calibration))
    errors = regression_errors(calibration[TARGET_COLUMN].to_numpy(dtype=float), predicted)
    return {
        "train_end_year": train_end_year,
        "scored_years": list(LATE_VALIDATION_YEARS),
        "n_train_rows": int(len(selection)),
        "n_scored_rows": int(len(calibration)),
        "mae": errors["mae"],
        "rmse": errors["rmse"],
        "role": "limitation_check_not_a_fold",
    }


def learning_curve_interpretation(folds: Sequence[FoldMetrics]) -> str:
    first, last = folds[0], folds[-1]
    if last.validation_mae < first.validation_mae:
        direction = "fell"
    elif last.validation_mae > first.validation_mae:
        direction = "rose"
    else:
        direction = "stayed flat"
    late = [fold for fold in folds if fold.validation_year in LATE_VALIDATION_YEARS]
    late_gap_usd = statistics.fmean(fold.validation_mae - fold.train_mae for fold in late)
    return (
        f"Each point is one validation year. Training history grows from {first.n_train_rows} "
        f"months (validation {first.validation_year}) to {last.n_train_rows} months "
        f"(validation {last.validation_year}). Validation MAE {direction} from "
        f"{_usd(first.validation_mae)} to {_usd(last.validation_mae)}. On the 2022 and 2023 "
        f"folds, validation MAE exceeds in-sample training MAE by {_usd(late_gap_usd)} "
        "on average. There is no shaded band, because each point is one chronological "
        "prefix rather than a repeated sample. The fold-to-fold spread is the sample "
        "standard deviation in the table."
    )


def plot_learning_curve(folds: Sequence[FoldMetrics], path: Path) -> None:
    sizes = [fold.n_train_rows for fold in folds]
    if sizes != sorted(sizes) or len(set(sizes)) != len(sizes):
        raise EvaluationError("Learning-curve training sizes must strictly increase")
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(
        sizes,
        [fold.train_mae for fold in folds],
        color="#1e3a5f",
        marker="o",
        linewidth=2,
        label="Training MAE (USD)",
    )
    ax.plot(
        sizes,
        [fold.validation_mae for fold in folds],
        color="#c2410c",
        marker="s",
        linewidth=2,
        label="Validation MAE (USD)",
    )
    ax.set_title("HealthCore sales forecast learning curve — MAE (USD)")
    ax.set_xlabel("Training months (chronological prefix)")
    ax.set_ylabel("MAE (USD)")
    ax.yaxis.set_major_formatter(lambda value, _pos: f"${value:,.0f}")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def render_report(results: Mapping[str, Any]) -> str:
    """Write the technical report from computed results."""
    diagnosis = results["diagnosis"]
    summary = results["summary"]
    folds = results["folds"]
    side = results["side_score"]
    lines = [
        "# HealthCore sales-forecast evaluation",
        "",
        "## Executive diagnosis and staging recommendation",
        "",
        f"**Diagnosis: {diagnosis['display_label']}.** {diagnosis['staging_sentence']}",
        "",
        diagnosis["next_action"],
        "",
        "This verdict uses the five training-period folds and the learning curve. "
        f"The held-out years {results['held_out_test_years'][0]} and "
        f"{results['held_out_test_years'][1]} are not cross-validation folds, and they "
        "were not used to choose the diagnosis or the staging sentence.",
        "",
        "## Company context and the cost of an error",
        "",
        "HealthCore is the assigned company. The forecast series is one consolidated "
        "monthly revenue row, not one row per clinic. The target is `revenue_usd`, in "
        "US dollars. `CONTEXT.md` does not say whether overestimating revenue or "
        "underestimating revenue is more costly, so this report does not rank those "
        "directions. MAE is the primary metric: it is the typical absolute miss in "
        "dollars, and the existing forest was selected with MAE. RMSE is reported beside "
        "it because squaring gives extra weight to large misses. Neither metric is "
        "universally better.",
        "",
        "## Dataset scope",
        "",
        f"Source: `{results['source']}`. Training years are {results['train_years'][0]}–"
        f"{results['train_years'][-1]}. After the 12-month lag warmup, "
        f"{results['n_train_feature_rows']} feature rows remain, covering "
        f"{results['feature_year_min']}–{results['feature_year_max']}. The horizon is "
        "rolling one month ahead. The entity is `region=consolidated`. The frequency is "
        "one row per month. "
        f"{results['held_out_test_years'][0]} and {results['held_out_test_years'][1]} "
        "stay outside the folds.",
        "",
        "## Model and features",
        "",
        "The model is the existing `RandomForestRegressor` with frozen settings "
        f"n_estimators={results['hyperparameters']['n_estimators']}, "
        f"max_depth={results['hyperparameters']['max_depth']}, "
        f"min_samples_leaf={results['hyperparameters']['min_samples_leaf']}, "
        f"random_state={results['random_state']}. Settings were read from "
        f"`{results['hyperparameters_source']}` and were not searched again. "
        "No scaler is used. Features: "
        + ", ".join(f"`{column}`" for column in results["feature_columns"])
        + ". Same-month `visits_count` and `avg_revenue_per_visit_usd` stay excluded.",
        "",
        "## Cross-validation design",
        "",
        "Five expanding year folds cover validation years "
        + ", ".join(str(year) for year in results["validation_years"])
        + ". Each training window is sorted, and its latest month is strictly earlier "
        "than the validation year's first month. Inside a validation year, a month may "
        "use the real revenue from earlier months, because the task is one month ahead. "
        "The forest for each fold is fit on that fold's training rows only. "
        "Validation years "
        + ", ".join(str(year) for year in results["selection_overlap_years"])
        + " overlap the months that chose these settings, so those three folds can make "
        "the five-fold mean look rosy. Seasonal naive is `revenue_lag_12` on the same "
        "validation rows. The spread is the sample standard deviation, which divides by "
        "4 when there are five folds.",
        "",
        "## Fold results",
        "",
        "Amounts are USD.",
        "",
        "| Validation year | Training months | Training MAE | Training RMSE | Validation MAE | Validation RMSE | Seasonal-naive validation MAE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for fold in folds:
        lines.append(
            f"| {fold['validation_year']} | {fold['n_train_rows']} | "
            f"{fold['train_mae']:.2f} | {fold['train_rmse']:.2f} | "
            f"{fold['validation_mae']:.2f} | {fold['validation_rmse']:.2f} | "
            f"{fold['naive_validation_mae']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Mean ± sample standard deviation",
            "",
            f"- Training MAE: {_mean_std(summary['train_mae'])}",
            f"- Training RMSE: {_mean_std(summary['train_rmse'])}",
            f"- Validation MAE (primary): {_mean_std(summary['validation_mae'])}",
            f"- Validation RMSE: {_mean_std(summary['validation_rmse'])}",
            f"- Seasonal-naive validation MAE: {_mean_std(summary['naive_validation_mae'])}",
            "",
            "## Training versus validation error",
            "",
            "Training error is the in-sample error on the months just used to fit that fold. "
            "A random forest with `min_samples_leaf=2` can look very accurate on those months. "
            f"Mean training MAE is {_mean_std(summary['train_mae'])}. Mean validation MAE is "
            f"{_mean_std(summary['validation_mae'])}. The diagnosis uses the 2022–2023 gap, "
            "when more history is available, rather than treating every early gap as overfitting.",
            "",
            "## Learning curve",
            "",
            results["learning_curve_interpretation"],
            "",
            f"![Learning curve: MAE in USD]({results['learning_curve_relative_to_report']})",
            "",
            "## Fit classification",
            "",
            diagnosis["rule"],
            "",
            f"The average 2022–2023 gap ratio is {diagnosis['late_gap_ratio']:.2f}. "
            f"That gap is {_usd(diagnosis['late_gap_usd'])} of validation MAE minus training MAE. "
            f"Mean validation MAE is {_usd(diagnosis['mean_validation_mae'])}. "
            f"Mean seasonal-naive validation MAE is {_usd(diagnosis['mean_naive_validation_mae'])}. "
            f"The classification is **{diagnosis['display_label']}**.",
            "",
            "## Next action",
            "",
            diagnosis["next_action"],
            "",
            "## Limitations and reproducibility",
            "",
            "The 2022–2023 side score fits the forest on feature rows through "
            f"{side['train_end_year']} ({side['n_train_rows']} months) and scores the next "
            f"{side['n_scored_rows']} months one month at a time. Its MAE is {_usd(side['mae'])} "
            f"and its RMSE is {_usd(side['rmse'])}. This score is a limitation check. It is not "
            "a sixth cross-validation fold, and it is not included in the five-fold mean.",
            "",
            "`CONTEXT.md` does not identify a costlier direction of error. The five-fold mean "
            "includes 2019–2021, which helped choose the frozen settings. In-sample training "
            "error understates the error of a forest. The learning curve has five chronological "
            "points and no uncertainty band.",
            "",
            "Re-run from the repository root:",
            "",
            "```bash",
            "uv --directory scripts/sales_forecast run python ../eval_sales_forecast.py",
            "```",
            "",
            f"Fold metrics: `{results['artifacts']['cv_metrics']}`. "
            f"Learning curve: `{results['artifacts']['learning_curve']}`. "
            "Dollar figures in this report are written from that run.",
            "",
        ]
    )
    return "\n".join(lines)


def run_evaluation(repo_root: Path) -> dict[str, Any]:
    """Score the frozen model on training-year folds and write the report artifacts."""
    raw_path = repo_root / RAW_RELATIVE_PATH
    eval_dir = repo_root / EVAL_RELATIVE_DIR
    metrics_path = eval_dir / "metrics.json"
    params = load_frozen_hyperparameters(metrics_path)
    assert_evaluation_population(pd.read_csv(raw_path))
    featured = training_feature_frame(load_sales(raw_path))
    windows = diagnostic_folds(featured)
    assert_healthcore_folds(windows)
    fold_metrics = [score_fold(window, params) for window in windows]
    summary = summarize_folds(fold_metrics)
    diagnosis = diagnose(fold_metrics)
    side = score_side_window(featured, params)
    interpretation = learning_curve_interpretation(fold_metrics)

    plot_path = eval_dir / LEARNING_CURVE_NAME
    json_path = eval_dir / CV_METRICS_NAME
    report_path = repo_root / REPORT_RELATIVE_PATH
    plot_learning_curve(fold_metrics, plot_path)

    payload: dict[str, Any] = {
        "primary_metric": "mae_usd",
        "primary_metric_reason": (
            "CONTEXT.md does not rank over-prediction against under-prediction. "
            "MAE is primary because it measures the typical absolute miss in USD and "
            "because the frozen forest was selected with MAE."
        ),
        "source": str(RAW_RELATIVE_PATH),
        "hyperparameters_source": str(metrics_path.relative_to(repo_root)),
        "hyperparameters": params,
        "random_state": SEED,
        "model_class": "RandomForestRegressor",
        "feature_columns": list(FEATURE_COLUMNS),
        "train_years": list(TRAIN_YEARS),
        "held_out_test_years": list(TEST_YEARS),
        "validation_years": [fold.validation_year for fold in fold_metrics],
        "selection_overlap_years": list(SELECTION_OVERLAP_YEARS),
        "n_train_feature_rows": int(len(featured)),
        "feature_year_min": int(featured[TIME_COLUMN].dt.year.min()),
        "feature_year_max": int(featured[TIME_COLUMN].dt.year.max()),
        "folds": [asdict(fold) for fold in fold_metrics],
        "summary": summary,
        "side_score": side,
        "diagnosis": diagnosis,
        "learning_curve_interpretation": interpretation,
        "learning_curve_relative_to_report": f"sales_forecast/{LEARNING_CURVE_NAME}",
        "artifacts": {
            "learning_curve": str(plot_path.relative_to(repo_root)),
            "cv_metrics": str(json_path.relative_to(repo_root)),
            "report": str(report_path.relative_to(repo_root)),
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    report_path.write_text(render_report(payload))
    print(f"Diagnosis: {diagnosis['display_label']}")
    print(diagnosis["staging_sentence"])
    print(f"Wrote {report_path.relative_to(repo_root)}")
    print(f"Wrote {json_path.relative_to(repo_root)}")
    print(f"Wrote {plot_path.relative_to(repo_root)}")
    return payload


def _assert_expanding_order(windows: Sequence[FoldWindow]) -> None:
    validation_starts: list[pd.Timestamp] = []
    for window in windows:
        validation_times = pd.to_datetime(window.validation[TIME_COLUMN])
        train_times = pd.to_datetime(window.train[TIME_COLUMN])
        if not bool(train_times.is_monotonic_increasing):
            raise EvaluationError("Training timestamps are not ordered")
        if not bool(validation_times.is_monotonic_increasing):
            raise EvaluationError("Validation timestamps are not ordered")
        if train_times.max() >= validation_times.min():
            raise EvaluationError("A training timestamp is not earlier than validation")
        validation_starts.append(pd.Timestamp(validation_times.min()))
    years = [window.validation_year for window in windows]
    if years != sorted(years) or len(set(years)) != len(years):
        raise EvaluationError("Validation years do not move forward")
    for earlier, later in zip(validation_starts, validation_starts[1:]):
        if later <= earlier:
            raise EvaluationError("Validation windows do not move forward through time")
    for index, window in enumerate(windows):
        future_years = {later.validation_year for later in windows[index + 1 :]}
        if future_years & set(window.train_years):
            raise EvaluationError(
                "A later validation year appears in an earlier fold's training years"
            )


def _metric_summary(values: Sequence[float]) -> dict[str, float | int]:
    return {
        "mean": float(statistics.fmean(values)),
        "sample_std": sample_std(values),
        "n": len(values),
        "ddof": 1,
    }


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _mean_std(summary: Mapping[str, Any]) -> str:
    return (
        f"{_usd(float(summary['mean']))} ± {_usd(float(summary['sample_std']))} "
        f"(sample standard deviation, n={int(summary['n'])})"
    )


def _iso_month(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")
