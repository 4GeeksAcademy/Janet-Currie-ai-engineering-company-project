"""Random Forest selection and fitting (training years only)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from .constants import PARAM_GRID, SEED, TARGET_COLUMN, TIME_COLUMN
from .features import feature_matrix


def expanding_year_folds(frame: pd.DataFrame) -> Iterator[tuple[pd.DataFrame, pd.DataFrame]]:
    years = sorted(int(year) for year in frame[TIME_COLUMN].dt.year.unique())
    for index, val_year in enumerate(years):
        train_years = years[:index]
        if len(train_years) < 2:
            continue
        train = frame.loc[frame[TIME_COLUMN].dt.year.isin(train_years)]
        val = frame.loc[frame[TIME_COLUMN].dt.year == val_year]
        if train.empty or val.empty:
            continue
        yield train, val


def make_regressor(params: Mapping[str, int]) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=int(params["n_estimators"]),
        max_depth=int(params["max_depth"]),
        min_samples_leaf=int(params["min_samples_leaf"]),
        random_state=SEED,
        n_jobs=1,
    )


def select_random_forest(
    selection_frame: pd.DataFrame,
    *,
    grid: Sequence[Mapping[str, int]] = PARAM_GRID,
) -> tuple[dict[str, int], float]:
    """Pick RF params by mean expanding-window MAE inside selection_frame."""
    folds = list(expanding_year_folds(selection_frame))
    if not folds:
        raise ValueError("Not enough years in the selection frame for time-aware validation")

    best_params: dict[str, int] | None = None
    best_mae = float("inf")
    for params in grid:
        fold_maes: list[float] = []
        for train, val in folds:
            model = make_regressor(params)
            model.fit(feature_matrix(train), train[TARGET_COLUMN].astype(float))
            preds = model.predict(feature_matrix(val))
            fold_maes.append(mean_absolute_error(val[TARGET_COLUMN], preds))
        mean_mae = float(sum(fold_maes) / len(fold_maes))
        if mean_mae < best_mae:
            best_mae = mean_mae
            best_params = dict(params)
    if best_params is None:
        raise ValueError("Hyperparameter grid was empty")
    return best_params, best_mae


def fit_random_forest(frame: pd.DataFrame, params: Mapping[str, int]) -> RandomForestRegressor:
    model = make_regressor(params)
    model.fit(feature_matrix(frame), frame[TARGET_COLUMN].astype(float))
    return model
