"""Test-set metrics: sklearn errors, ranking Gini, residual K2, PSI."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .constants import PSI_BINS, PSI_EPSILON


def regression_errors(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mse = float(mean_squared_error(actual, predicted))
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mse))
    mean_actual = float(np.mean(actual))
    rmse_pct = float(rmse / mean_actual * 100.0) if mean_actual != 0 else float("nan")
    return {
        "mse": mse,
        "mae": mae,
        "rmse": rmse,
        "rmse_pct_of_mean": rmse_pct,
        "r2": float(r2_score(actual, predicted)),
        "mean_actual": mean_actual,
    }


def _lorenz_gini(actual: np.ndarray, rank_scores: np.ndarray) -> float:
    n = actual.size
    order = np.argsort(-rank_scores, kind="mergesort")
    sorted_actual = actual[order]
    total = sorted_actual.sum()
    if total == 0:
        return 0.0
    cumulative = np.cumsum(sorted_actual)
    gini_sum = cumulative.sum() / total - (n + 1) / 2.0
    return float(gini_sum / n)


def normalized_gini(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Normalized ranking Gini of predictions versus a continuous target."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.size < 2:
        raise ValueError("Gini requires at least two observations")
    if np.unique(predicted).size == 1:
        return 0.0
    perfect = _lorenz_gini(actual, actual)
    if perfect == 0:
        return 0.0
    return _lorenz_gini(actual, predicted) / perfect


def residual_k2(residuals: np.ndarray) -> dict[str, float]:
    """D'Agostino-Pearson K² normality test on residuals.

    Closer to 0 means residuals look more normal. This is not R².
    """
    values = np.asarray(residuals, dtype=float)
    if values.size < 8:
        raise ValueError("K2 / normaltest requires at least 8 residuals")
    statistic, pvalue = stats.normaltest(values)
    return {"k2": float(statistic), "k2_pvalue": float(pvalue)}


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    *,
    n_bins: int = PSI_BINS,
    epsilon: float = PSI_EPSILON,
) -> float:
    """PSI of current vs reference using quantile bins fit on reference only."""
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    if reference.size == 0 or current.size == 0:
        raise ValueError("PSI requires non-empty reference and current samples")
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if edges.size < 2:
        raise ValueError("Cannot form PSI bins from the reference sample")
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    ref_pct = ref_counts.astype(float) / max(ref_counts.sum(), 1)
    cur_pct = cur_counts.astype(float) / max(cur_counts.sum(), 1)
    ref_pct = np.clip(ref_pct, epsilon, None)
    cur_pct = np.clip(cur_pct, epsilon, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def evaluate_predictions(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    prefix: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in regression_errors(actual, predicted).items():
        payload[f"{prefix}_{key}"] = value
    payload[f"{prefix}_gini"] = normalized_gini(actual, predicted)
    payload.update({f"{prefix}_{key}": value for key, value in residual_k2(actual - predicted).items()})
    return payload
