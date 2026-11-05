"""Split-conformal prediction intervals (training calibration only)."""

from __future__ import annotations

import numpy as np

from .constants import INTERVAL_COVERAGE


def conformal_quantile(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    coverage: float = INTERVAL_COVERAGE,
) -> float:
    residuals = np.abs(np.asarray(actual, dtype=float) - np.asarray(predicted, dtype=float))
    n = residuals.size
    if n == 0:
        raise ValueError("Calibration residuals are empty")
    q_level = min(1.0, float(np.ceil((n + 1) * coverage) / n))
    return float(np.quantile(residuals, q_level, method="higher"))


def prediction_interval(
    point: np.ndarray,
    quantile: float,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(point, dtype=float)
    lower = values - quantile
    upper = values + quantile
    if np.any(lower > values) or np.any(values > upper):
        raise ValueError("Interval ordering violated: lower <= prediction <= upper")
    return lower, upper


def interval_diagnostics(
    actual: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    inside = (actual >= lower) & (actual <= upper)
    return {
        "coverage": float(np.mean(inside)),
        "mean_width": float(np.mean(upper - lower)),
    }
