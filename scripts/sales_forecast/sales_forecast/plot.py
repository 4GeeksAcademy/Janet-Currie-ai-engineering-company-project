"""Chronological test-period plot with actuals, predictions, and interval."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .constants import INTERVAL_COVERAGE, TARGET_COLUMN, TIME_COLUMN


def plot_test_forecast(
    test: pd.DataFrame,
    *,
    predicted: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    path: Path,
    model_name: str = "RandomForestRegressor",
) -> None:
    times = pd.to_datetime(test[TIME_COLUMN])
    actual = test[TARGET_COLUMN].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.fill_between(
        times,
        lower,
        upper,
        color="#93c5fd",
        alpha=0.45,
        label=f"{int(INTERVAL_COVERAGE * 100)}% split-conformal prediction interval",
    )
    ax.plot(times, actual, color="#1e3a5f", marker="o", linewidth=2, label="Actual revenue")
    ax.plot(
        times,
        predicted,
        color="#c2410c",
        marker="s",
        linewidth=2,
        label=f"{model_name} (one-month-ahead)",
    )
    ax.set_title(f"HealthCore monthly revenue — {model_name} vs actual (2024–2025 holdout)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (USD)")
    ax.yaxis.set_major_formatter(lambda value, _pos: f"${value / 1_000_000:.1f}M")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
