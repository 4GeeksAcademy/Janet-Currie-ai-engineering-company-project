"""Metric edge cases: PSI bins, Gini ties, residual K2, report card."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "sales_forecast"
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from sales_forecast.conclusion import report_card
from sales_forecast.metrics import normalized_gini, population_stability_index, residual_k2


def test_psi_empty_bins_do_not_divide_by_zero() -> None:
    reference = np.arange(1.0, 21.0)
    current = np.array([1.0, 1.1, 1.2, 1.3])  # piles into the lowest bin
    value = population_stability_index(reference, current, n_bins=5)
    assert np.isfinite(value)
    assert value >= 0


def test_gini_perfect_ranking_is_one() -> None:
    actual = np.array([1.0, 2.0, 3.0, 4.0])
    assert normalized_gini(actual, actual) == pytest.approx(1.0)


def test_gini_constant_predictions_near_zero() -> None:
    actual = np.array([1.0, 2.0, 3.0, 4.0])
    predicted = np.array([7.0, 7.0, 7.0, 7.0])
    assert normalized_gini(actual, predicted) == pytest.approx(0.0)


def test_gini_tied_actuals_returns_zero() -> None:
    actual = np.array([5.0, 5.0, 5.0, 5.0])
    predicted = np.array([1.0, 2.0, 3.0, 4.0])
    assert normalized_gini(actual, predicted) == pytest.approx(0.0)


def test_k2_is_smaller_for_normal_than_skewed() -> None:
    rng = np.random.default_rng(42)
    normal = rng.normal(0, 1, size=200)
    skewed = rng.lognormal(mean=0, sigma=1.5, size=200)
    assert residual_k2(normal)["k2"] < residual_k2(skewed)["k2"]


def test_report_card_unsupported_when_worse_than_baseline() -> None:
    result = report_card(model_mae=100.0, baseline_mae=50.0, gini=0.9, coverage=0.9)
    assert result["decision"] == "unsupported"


def test_report_card_supported_when_all_checks_pass() -> None:
    result = report_card(model_mae=40.0, baseline_mae=50.0, gini=0.6, coverage=0.8)
    assert result["decision"] == "supported"


def test_report_card_uncertain_when_ranking_fails() -> None:
    result = report_card(model_mae=40.0, baseline_mae=50.0, gini=0.0, coverage=0.8)
    assert result["decision"] == "uncertain"
