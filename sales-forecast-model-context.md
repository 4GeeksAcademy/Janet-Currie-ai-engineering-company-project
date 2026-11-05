# HealthCore Regression Model — Implementation Context

## Purpose

This document is an implementation document for the HealthCore sales-forecast regression project. Use it together with the separate HealthCore-briefing.en.md already supplied. That briefing is the authority for the dataset structure, field meanings, target, KPIs, business constraints, file locations, and required deliverables. This document explains how to turn those HealthCore-specific facts into an honestly trained and evaluated regression model.

The central question is:

> Can HealthCore's available historical data predict sales for coming months with an error and uncertainty level that Finance considers acceptable?

The result is a feasibility assessment, not merely a trained estimator. It must demonstrate temporal generalization, quantify point error and uncertainty, and state whether the evidence supports investing in a future executive dashboard.

## Source-of-Truth Order

Resolve implementation details in this order:

1. The HealthCore briefing: company-specific schema, definitions, KPI formulas or thresholds, business rules, and deliverables.
2. This context: modeling, leakage prevention, evaluation, uncertainty, validation, and reporting instructions.
3. The existing monorepo: current project structure, package conventions, reusable utilities, and test patterns.
4. The assignment screenshots: minimum rubric requirements summarized below.

Do not replace an exact HealthCore rule with a generic assumption. If the briefing and this document appear to conflict, preserve the HealthCore rule and record the resolution in the implementation README or project documentation. If a required term remains ambiguous after inspecting the briefing and repository—especially `PSI`, `Gini`, or `K2 Score`—do not silently guess; make the definition and formula explicit before presenting results.

## Required Outcome

Implement the HealthCore deliverables so that they:

- use the provided historical dataset without generating, simulating, or rewriting source data;
- forecast the exact continuous target defined in the HealthCore briefing;
- use the earliest eight years for training and the most recent two years as a completely held-out temporal test period;
- prevent target, future, preprocessing, and model-selection leakage;
- use either Random Forest regression or XGBoost regression as the final model and justify the choice for HealthCore;
- calculate the rubric's MSE, PSI, Gini, and K2 Score using explicit, reproducible definitions;
- include at least one finance-readable error measure in natural target units;
- show predictions, actual values, and a defensible variability or prediction interval over the two test years;
- fix all relevant random seeds;
- include a focused unit test proving the 8-year/2-year split and absence of overlap; and
- conclude whether the observed holdout performance meets the HealthCore acceptance criteria, without overstating what the experiment proves.

## Scope Boundaries

### In scope

- schema and data-quality validation;
- temporal feature preparation;
- leakage-safe train/validation/test design;
- training and selection of one allowed tree-based regression model;
- point predictions and prediction intervals;
- the mandated metrics and useful supporting diagnostics;
- the required visualization, documentation, and tests;
- reproducible local execution using the monorepo's established tooling.

### Out of scope unless the HealthCore briefing explicitly requires it

- building an executive dashboard;
- deploying or serving the model;
- changing production systems or production data;
- creating synthetic sales history;
- replacing the requested regression model with a classifier or an unrelated forecasting library;
- using external data not approved by the briefing;
- tuning against the two-year test set;
- committing, pushing, opening a pull request, merging, or deploying without direct authorization.

## Repository and Environment Rules

Work in the existing company monorepo, not a new repository. Before changing code, inspect the actual checkout and the complete HealthCore briefing.

- Use the repository's existing project and package layout. Do not invent paths when the briefing specifies them.
- The expected raw-data location from the assignment is `data/raw/<company>_sales.csv`; use the exact HealthCore path from the briefing/repository.
- Never modify the raw dataset in place. Derived data, predictions, metrics, and plots must go only to the established output locations.
- Use `uv` for environment and dependency management. If `pyproject.toml` exists, extend it rather than running `uv init`. Add only missing dependencies with `uv add`; do not use `pip install` or Pipenv.
- Reuse compatible existing dependencies and utilities before adding new ones.
- If repository workflow calls for a feature branch, the assignment's suggested name is `feature/sales-forecast-model`; verify the actual base branch and working-tree state first, and do not discard existing changes.
- Fix `random_state`/`seed` everywhere stochastic behavior occurs and centralize the value so tests and runs use the same seed.

## First Step: Read and Convert the HealthCore Briefing into a Data Contract

Before modeling, extract the following facts from the briefing and reflect them in configuration, validation, or documentation:

| Contract item | Required resolution |
| --- | --- |
| Source file | Exact repository-relative path and file format. |
| Time field | Exact column, parse format, time zone if relevant, and observation frequency. |
| Target | Exact continuous field to predict, units, aggregation rule, and whether zero/negative values are valid. |
| Row grain | What one row represents before and after any aggregation. |
| Predictors | Exact allowed feature columns and their business availability at prediction time. |
| Identifiers | Columns that identify records but must not become misleading numeric predictors. |
| Categories | Allowed values, unknown-value behavior, and encoding needs. |
| Missing data | Business meaning and approved handling per field. |
| Seasonality | The known HealthCore seasonal pattern that must be preserved and represented. |
| Growth/trend | The known historical growth pattern and any constraint on transformations. |
| KPIs | Exact formulas, units, thresholds, segments, and required reporting format. |
| Forecast use | Forecast origin, horizon, and which future covariates are genuinely available. |
| Deliverables | Exact file names, directories, commands, and documentation required by HealthCore. |

Fail fast with a clear message if required columns are absent, dates cannot be parsed, the target is unusable, the row grain is inconsistent, or the dataset does not support the required temporal split. Do not conceal a schema mismatch by renaming unrelated columns or fabricating values.

## Data Inspection and Quality Checks

Perform read-only inspection of the source data before preprocessing. At minimum, record:

- row count, date range, observation frequency, unique years, and rows per period;
- column names, data types, target units, and basic target distribution;
- null, empty, invalid, duplicate, and non-finite values;
- missing time periods and duplicate timestamps at the expected grain;
- categorical cardinality and values outside the briefing's allowed domain;
- implausible target or feature values under HealthCore's business rules;
- whether the time series is ordered and whether aggregation is required;
- visible trend, seasonality, level shifts, and outliers; and
- whether all features would be known when each forecast is made.

Use business-aware handling for nulls and invalid values. Every drop, imputation, clipping rule, or transformation must be fit or derived from training data only when it learns a statistic. Report how many records each rule affects. Do not smooth away or rebalance the seasonality and growth behavior described in the HealthCore briefing.

## Temporal Split Contract

### Required holdout

Sort by the canonical HealthCore time field and split by complete calendar or business years as defined in the briefing:

- **training:** the earliest eight years;
- **test/checking:** the two most recent years.

The split is chronological, never random. The model, preprocessing statistics, feature selection, hyperparameter search, interval calibration, and model choice must not inspect test targets.

Before fitting, assert all of the following:

- the dataset contains the expected ten-year span or whatever exact ten-year representation the briefing defines;
- the selected training years and test years are complete enough for the stated evaluation;
- `max(train_time) < min(test_time)`;
- training and test year sets are disjoint;
- record identifiers or timestamps do not overlap across sets;
- every row belongs to exactly one set; and
- the test set consists of the most recent two years.

If there are more or fewer than ten usable years, partial boundary years, or a briefing-defined fiscal year, stop and reconcile the split with the briefing instead of silently taking an arbitrary row percentage.

### Training-only validation

The held-out two years are for the final unbiased evaluation only. Make model and hyperparameter decisions within the first eight years using a time-respecting validation scheme, preferably expanding-window or rolling-origin validation. Never use shuffled K-fold validation for time-dependent records.

Where the first eight years are too small for elaborate tuning, prefer a compact, predeclared search over a large adaptive search. The aim is an honest feasibility result, not maximum leaderboard performance.

## Define the Forecasting Experiment Before Feature Engineering

State the forecast origin and horizon that match Finance's question. Distinguish between these two legitimate but different experiments:

1. **Fixed-origin multi-month forecast:** all two test years are forecast from the end of training. Actual test targets are never used as lag inputs; recursive predictions or direct-horizon models are required.
2. **Rolling one-step forecast:** each period is forecast when the previous actual periods have become available. This permits observed prior-period targets at each new origin, but only after those periods would exist in real operations.

Use the mode required by the HealthCore briefing. If it does not specify one, choose the mode that matches the promised business workflow, document the choice, and do not describe rolling one-step accuracy as proof of fixed-origin 24-month performance.

Any exogenous predictor used for a future period must either be known at forecast time or have its own documented forecasting/source process. A predictor that is only recorded after the target occurs is leakage even if it appears as an ordinary CSV column.

## Feature Engineering Rules

Build features from the HealthCore contract, not from generic column guesses. Candidate feature groups may include the following only when the source data and forecast workflow support them:

- calendar features such as month, quarter, fiscal period, or approved holidays;
- a monotonic time index for long-run trend;
- cyclical encodings for genuinely cyclical calendar fields;
- approved business, product, location, or operational attributes known at prediction time;
- target lags; and
- shifted rolling summaries computed exclusively from observations available before the forecast origin.

Leakage safeguards are mandatory:

- lag and rolling features must be shifted before rolling statistics are computed;
- no centered windows or future-looking aggregates;
- encoders, imputers, scalers, selectors, and other learned transforms fit on training data only;
- no target-derived aggregate may include the row being predicted or any future row;
- identifiers are not numeric features unless the briefing supplies a meaningful encoding strategy;
- post-outcome fields are excluded; and
- feature-generation behavior at the train/test boundary must match production forecasting behavior.

Tree ensembles do not require feature scaling to compare split thresholds. Satisfy the rubric's instruction to “scale the variables that need it” by explicitly assessing the feature set and documenting that Random Forest/XGBoost features do not need scaling when that is the conclusion. If a supporting model or transformation does require scaling, place it in a pipeline and fit it on training folds only. Do not add scaling mechanically or fit it on the full dataset.

## Baselines and Feasibility Standard

An error value has little meaning without a reference. Evaluate at least one simple, leakage-safe baseline appropriate to HealthCore's frequency and seasonality—for example, a last-observation, seasonal-naive, or historical seasonal-average forecast. Select the baseline from the known seasonal pattern in the briefing.

The final model should improve meaningfully on the baseline and satisfy the briefing's business threshold. If it does not, report that result honestly. Do not tune on the test set until the conclusion changes.

## Allowed Model and Selection Rationale

The final trained estimator must be one of:

- `RandomForestRegressor`; or
- an XGBoost regressor compatible with the repository's scikit-learn workflow.

Choose one final model. Justify it using evidence available without the test targets, considering:

- dataset size and feature dimensionality;
- nonlinearities and interactions;
- training and tuning time;
- operational dependency cost;
- sensitivity to hyperparameters and overfitting;
- explainability needs for Finance;
- missing/categorical feature behavior after preprocessing;
- reproducibility; and
- the interval-estimation approach.

Random Forest is a strong default when interpretability, modest tuning, and dependency simplicity matter. XGBoost may be justified when training-only validation shows a meaningful performance advantage and the added tuning and explanation burden is acceptable. Do not claim that either algorithm is universally better.

If both are compared during development, keep the comparison inside time-aware validation on the eight training years. Use the final two years exactly once for the locked final model and baseline report.

Keep tuning bounded and record the chosen parameters. Control tree depth/leaf size or equivalent capacity, and inspect the train-versus-validation gap for overfitting. Refit the selected pipeline on all eight training years only after model selection and interval calibration decisions are locked.

## Prediction Variability and Uncertainty

The required shaded variability area must be a documented interval, not decorative standard deviation and not a range calibrated from test errors. Define:

- what the interval represents (preferably a prediction interval for future observations);
- its nominal coverage, such as 80% or 95%;
- how it is estimated;
- which training-only data calibrates it; and
- its limitations under time dependence and distribution shift.

Preferred approaches are:

- time-respecting split conformal prediction using a calibration segment taken from the eight-year training period;
- rolling/blocked conformal residual calibration; or
- model-specific quantile estimates that are calibrated and validated without the final test targets.

For Random Forest, raw dispersion across trees is not automatically a valid prediction interval; if used as a variability heuristic, label it accurately and do not claim nominal coverage. For XGBoost, lower and upper quantile models require appropriate quantile objectives and must be trained without test leakage.

On the final test set, report empirical interval coverage and average interval width as diagnostics. Test outcomes may evaluate the already-fixed interval but must not set or widen it.

## Required Metrics

Calculate and report the following on the held-out two-year test period, using the exact HealthCore or course definitions when supplied.

### MSE

Mean squared error is `mean((actual - prediction) ** 2)`. It heavily penalizes large misses but is expressed in squared target units, so it is not the clearest headline for Finance.

### PSI

Population Stability Index normally compares a reference distribution with a current distribution. Use training as the reference and test as the current population, with bin edges learned from training only. State exactly which variable(s) are measured, how bins and zero counts are handled, and how results are aggregated. Report it as a test-period drift diagnostic; do not present PSI as a direct prediction-error metric.

If the HealthCore briefing defines PSI differently, use that definition instead and document the formula.

### Gini

For a continuous target, use the briefing's regression Gini or normalized Gini definition, calculated from test actuals and predictions. State ordering, tie handling, normalization, and interpretation. Do not substitute classification ROC-AUC unless the briefing explicitly requires it.

### K2 Score

`K2 Score` is not a universally standard regression metric. Search the HealthCore briefing, course material present in the repository, and existing project utilities for its intended definition. Implement that exact formula and cite it in project documentation. Do not silently rename R-squared, explained variance, Cohen's kappa, or a residual-normality statistic as K2.

If the supplied materials never define K2, surface the ambiguity before finalizing the implementation. If work is authorized to continue with an explicit assumption, document the chosen formula, source, expected range, direction of improvement, and edge-case behavior in both code and README.

### Finance-readable supporting metric

Also report at least one error measure in the target's natural units, normally MAE and/or RMSE. Explain it in business language using the real HealthCore units. Add a percentage metric only if zero and near-zero actuals are handled transparently; never use raw MAPE when it can divide by zero or become misleading.

For every metric, document:

- formula or library function;
- input series and evaluation population;
- units and direction of improvement;
- edge-case handling;
- value for the final model and baseline; and
- relevance and limitations for Finance.

Do not claim that low MSE alone proves feasibility. Consider natural-unit error, baseline improvement, time-localized misses, stability/drift, ranking behavior where relevant, and interval calibration.

## Evaluation Diagnostics

In addition to aggregate metrics, inspect error by the time and business segments mandated in the HealthCore briefing. At minimum, examine:

- residuals over chronological time;
- performance by month/season or the briefing's seasonal units;
- bias (mean signed error), especially systematic over- or under-forecasting;
- the largest misses and whether they align with explainable events;
- first versus second test year, to reveal degradation with horizon or drift;
- interval coverage and width over time; and
- any required HealthCore KPI segment.

Do not use these test diagnostics to repeatedly retune the model. They support the final feasibility explanation and identify future work.

## Visualization Contract

Produce the required chronological visualization over the complete two-year test period. It must include:

- actual HealthCore target values;
- final model point predictions;
- a clearly labeled shaded variability/prediction interval;
- meaningful time and target-unit axes;
- model name, test period, and interval coverage/meaning;
- a legend; and
- readable formatting at the dataset's real frequency.

Do not plot shuffled rows. Do not show only point predictions. Do not imply the shaded area is a confidence or prediction interval unless the method supports that label. If the plot is aggregated for readability, calculate metrics at the required original evaluation grain and state the plot aggregation.

Save the figure to the HealthCore deliverable path and make generation reproducible from the documented command.

## Testing Requirements

Follow the repository's existing test conventions. At minimum, add a focused unit test under `tests/pipelines/` (or the exact HealthCore-mandated equivalent) proving that:

- the earliest eight years are assigned to training;
- the most recent two years are assigned to test;
- year/timestamp sets do not overlap;
- every eligible record is assigned once;
- the chronological boundary is strict; and
- the result is independent of input row order if the splitter is responsible for sorting.

Also add proportionate tests for newly introduced behavior where applicable:

- missing or malformed date handling;
- insufficient or unexpected year coverage;
- lag/rolling features at the training/test boundary;
- train-only fitting of learned preprocessing;
- metric edge cases, particularly empty bins/zero counts for PSI, tied or constant values for Gini, and the adopted K2 definition;
- reproducibility with the fixed seed; and
- prediction interval ordering (`lower <= prediction <= upper` when the method guarantees it).

Regression tests should use small deterministic fixtures, not overwrite the raw HealthCore data, and should verify observable contracts rather than estimator internals.

## Documentation and Reproducibility

The implementation README or briefing-specified documentation must state:

- business question and target definition;
- source data path, date range, grain, and units;
- exact train/test years and validation approach;
- forecast origin, horizon, and feature-availability assumptions;
- preprocessing and missing-data decisions;
- leakage protections;
- baseline and final-model choice rationale;
- fixed seed and important hyperparameters;
- exact definitions of MSE, PSI, Gini, K2, and supporting error metrics;
- interval method and nominal coverage;
- final test results and plot path;
- commands to install, train/evaluate, regenerate outputs, and run tests; and
- an evidence-based go/no-go conclusion against the HealthCore acceptance criteria.

Generated metric artifacts should include enough metadata to reproduce and interpret the run: data period, split years, target, model class, parameters, seed, metric definitions/version, and interval method. Do not rely on an untracked notebook's state as the only reproducible workflow.

## Suggested Implementation Sequence

1. Inspect the checkout, HealthCore briefing, raw-data contract, existing dependency setup, and test conventions.
2. Resolve the metric definitions—especially K2—before promising exact deliverables.
3. Implement schema validation and deterministic temporal splitting.
4. Add and run split/leakage regression tests.
5. Establish a seasonal or otherwise briefing-appropriate baseline.
6. Build leakage-safe feature preparation consistent with the declared forecast horizon.
7. Compare/choose the allowed model using time-aware validation inside the first eight years.
8. Lock preprocessing, features, parameters, seed, and interval procedure.
9. Refit on all eight training years and evaluate once on the two-year holdout.
10. Generate the mandated metrics, supporting diagnostics, interval coverage results, and visualization.
11. Run focused tests, then applicable lint/type/build or broader project checks.
12. Update documentation with actual commands, actual results, limitations, and the feasibility recommendation.

## Acceptance Checklist

The work is complete only when all applicable items below are true:

- [ ] The exact HealthCore dataset and schema are used; no synthetic or substituted data appears.
- [ ] Raw data remains unmodified and known seasonality/growth patterns are preserved.
- [ ] The temporal split is exactly eight earliest years versus two latest years.
- [ ] Training and test records do not overlap, and the split unit test passes.
- [ ] All learned preprocessing and model selection occur without test-target access.
- [ ] Forecast horizon and feature availability are explicit and internally consistent.
- [ ] The final model is Random Forest or XGBoost and its choice is justified for HealthCore.
- [ ] A fixed random seed makes repeated runs reproducible.
- [ ] A suitable naive baseline is reported.
- [ ] MSE, PSI, Gini, and K2 are calculated with explicit definitions and reported using the required test-period inputs.
- [ ] MAE and/or RMSE communicates error in Finance-readable units.
- [ ] The test visualization contains actuals, predictions, and a valid labeled variability range.
- [ ] Interval construction uses training-only calibration; test coverage is evaluation only.
- [ ] Required HealthCore KPIs, segments, constraints, paths, and deliverables are honored.
- [ ] Documentation explains why low MSE alone is insufficient.
- [ ] Actual validation commands and results are recorded; unrun checks are not claimed as passing.
- [ ] The conclusion states whether dashboard investment is supported, unsupported, or still uncertain under the briefing's threshold.

## Stop Conditions and Questions That Must Be Resolved

Pause and seek clarification rather than inventing a solution if any of the following remains unresolved after reading the HealthCore briefing and repository:

- the target or its units are unclear;
- the time field, row grain, or forecast horizon is unclear;
- the data does not contain the expected temporal coverage;
- future availability of a high-value predictor is uncertain;
- the course-specific K2 definition cannot be found;
- the briefing's KPI formula conflicts with a common library definition;
- the business acceptance threshold is absent but a go/no-go decision is demanded; or
- required deliverable paths conflict with current monorepo conventions.

When blocked, report the exact evidence found, the ambiguity, and the smallest decision needed. Do not manufacture HealthCore details to make the pipeline run.

## Final Reporting Standard

The final handoff to Finance/leadership should answer four questions plainly:

1. How far ahead and at what grain was the model tested?
2. How large are typical and large errors in HealthCore's real units, compared with a sensible baseline?
3. How often did actual outcomes fall inside the forecast interval, and how wide was it?
4. Does the evidence meet the HealthCore-defined threshold for proceeding to an executive dashboard?

Use cautious language. Performance on one two-year historical holdout demonstrates retrospective feasibility under those conditions; it does not guarantee future performance under new operational regimes, drift, policy changes, or shocks.
