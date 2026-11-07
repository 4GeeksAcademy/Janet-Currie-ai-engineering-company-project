"""Report-card go/no-go: no invented dollar cutoff."""

from __future__ import annotations

from typing import Any

from .constants import INTERVAL_COVERAGE


COVERAGE_TOLERANCE = 0.20


def report_card(
    *,
    model_mae: float,
    baseline_mae: float,
    gini: float,
    coverage: float,
    nominal_coverage: float = INTERVAL_COVERAGE,
) -> dict[str, Any]:
    beat_baseline = model_mae < baseline_mae
    ranks = gini > 0.0
    coverage_ok = coverage >= (nominal_coverage - COVERAGE_TOLERANCE)

    if not beat_baseline:
        decision = "unsupported"
        reason = (
            "Random Forest MAE does not beat the seasonal-naive baseline "
            "(same month last year), so the holdout does not support a dashboard."
        )
    elif beat_baseline and ranks and coverage_ok:
        decision = "supported"
        reason = (
            "The model beats seasonal-naive MAE, ranks quiet vs busy months "
            "(Gini > 0), and actuals usually land in the prediction interval."
        )
    else:
        decision = "uncertain"
        reason = (
            "The model beats the baseline on MAE, but ranking and/or interval "
            "coverage is mixed, so dashboard investment is still uncertain."
        )

    return {
        "decision": decision,
        "reason": reason,
        "beat_seasonal_naive_mae": beat_baseline,
        "gini_better_than_random": ranks,
        "interval_usually_covers": coverage_ok,
        "rules": {
            "unsupported_if": "model MAE >= seasonal-naive MAE",
            "supported_if": (
                "model MAE < baseline MAE AND Gini > 0 AND "
                f"coverage >= {nominal_coverage - COVERAGE_TOLERANCE:.0%}"
            ),
            "otherwise": "uncertain",
        },
    }
