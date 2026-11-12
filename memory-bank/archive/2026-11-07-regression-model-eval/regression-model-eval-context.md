# Project Context: Evaluating a Regression Model

## 1. Purpose of this document

This document defines the project’s purpose, scope, constraints, required outputs, validation expectations, and completion criteria. It does **not** contain an implementation and should not be treated as permission to redesign unrelated parts of the repository.

The authoritative assignment is:

- [4Geeks Academy — Evaluating a Regression Model](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-evaluating-regression-model/README.md)

If this document and the assignment ever disagree, follow the assignment. Company-specific facts must come from the assigned company’s `company-BRIEFING.md` (or the equivalent company briefing file already present in the monorepo), not from assumptions in this document.

## 2. Executive summary

The project must formally evaluate an **existing, already trained and hyperparameter-tuned sales-forecasting regression model** before it can be promoted to staging. The model was built in a previous project using time-derived features such as lags, rolling statistics, and calendar/seasonal signals.

The implementation must answer three questions with reproducible evidence:

1. Is the existing model underfitting, overfitting, or reasonably well fitted?
2. How stable is model performance when the training window changes?
3. If the evidence shows a problem, what specific corrective action follows from that diagnosis?

The answer must be supported by:

- time-aware cross-validation with at least five folds;
- explicit checks for chronological ordering and leakage;
- training and validation MAE and RMSE;
- fold results summarized as mean ± standard deviation;
- a learning-curve image;
- a written evaluation report with an explicit diagnosis and actionable recommendation; and
- a unit test proving the temporal folds preserve chronological order.

This is an **evaluation project**, not a request to create a new forecasting model, replace the existing model, deploy it, or build a user interface.

## 3. Project setting and prerequisite state

This work belongs in the student’s existing fork of the 4Geeks Academy company monorepo:

- [AI Engineering company project monorepo](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo)

Do not create a separate repository for the evaluation. The expected working branch is:

```text
feature/regression-model-eval
```

The repository is expected to contain the outputs of the preceding forecasting work:

- the trained/tuned regression model or a reproducible training pipeline;
- the company sales dataset and target definition;
- time-based feature engineering, including applicable lag, rolling, calendar, and seasonal features;
- an established temporal split of approximately eight years for training and two years for final testing; and
- existing project conventions for pipelines, tests, configuration, data paths, and dependency management.

Cursor must inspect the actual repository before changing anything. If any prerequisite is missing or cannot be reproduced, stop and document the exact missing prerequisite instead of silently building a different model or fabricating an equivalent artifact.

## 4. Mandatory discovery before implementation

Before writing code, Cursor must locate and read:

1. The assigned company briefing (`company-BRIEFING.md` or the repository’s equivalent).
2. The existing regression/forecasting training pipeline.
3. The current feature-engineering logic.
4. The target column, time column, entity identifiers, and forecast granularity.
5. The existing temporal train/test split and any saved model artifact.
6. Existing test patterns under `tests/`, especially `tests/pipelines/`.
7. The project dependency file and current Python tooling.
8. Any repository-local `AGENTS.md`, rules, memory-bank documents, or contributor instructions.

The discovery phase must resolve these values from the repository rather than guess them:

| Required fact | Source of truth |
|---|---|
| Assigned company/domain | Company briefing and repository context |
| Target field | Existing forecasting pipeline and company briefing |
| Timestamp/date field | Dataset schema and existing pipeline |
| Entity/group identifier(s) | Company briefing and dataset schema |
| Forecast frequency and horizon | Existing pipeline and briefing |
| Feature list and window sizes | Existing feature-engineering code |
| Model class and tuned parameters | Existing model/training code or saved metadata |
| Existing 8-year/2-year split boundaries | Existing pipeline/configuration |
| Costlier business error | Company briefing |
| Evaluation data/output conventions | Existing repository structure |

The assignment provides several possible company contexts. Do not assume Brasaland, Healthcore, Nexova, Trackflow, or any other company until the repository identifies the assigned context.

## 5. Business purpose

The evaluation is a staging gate. Its purpose is not merely to calculate a score; it is to help a technical reviewer decide whether the model is trustworthy enough to advance and, if it is not, what should be changed next.

The company briefing determines the operational meaning of prediction errors. In particular, the implementation must identify whether overestimating sales or underestimating sales is more harmful and explain how that context affects metric interpretation. Field names, IDs, units, and domain terminology in all code and documentation must match the briefing.

MAE and RMSE are both mandatory:

- **MAE** expresses the typical absolute error in the target’s units and weights each unit of error linearly.
- **RMSE** is more sensitive to occasional large misses because errors are squared before aggregation.

The report must choose one of these as the primary evaluation metric and justify the choice using the company’s actual cost profile. It must not state that one metric is universally superior. If the briefing identifies an asymmetric cost between overprediction and underprediction, the report should also discuss error direction using residuals or segmented error analysis; this may supplement, but does not replace, the required MAE and RMSE.

## 6. In scope

### 6.1 Reproduce the current model evaluation baseline

- Reuse the existing forecasting model, tuned hyperparameters, data preparation, and feature definitions.
- Preserve the final held-out test set. Do not use it to select folds, tune the model again, choose features, or decide the diagnosis.
- Establish reproducible training and validation metric calculations.
- Record enough configuration and boundaries for another developer to reproduce the results.

### 6.2 Time-aware cross-validation

Implement temporal cross-validation over the **training portion only**, using `TimeSeriesSplit` or an equivalent expanding/rolling-window strategy with at least five folds.

The cross-validation design must:

- preserve chronological order;
- never shuffle observations;
- ensure every validation interval occurs after its corresponding training interval;
- define behavior for duplicate timestamps and multiple entities if present;
- fit any learned preprocessing only on each fold’s training data;
- prevent lag and rolling features from using future observations; and
- report the primary metric for every fold plus mean and standard deviation.

If multiple rows share a timestamp, splitting by raw row index may divide the same time period across train and validation. Cursor must inspect the data and use time-group boundaries when necessary. If multiple entities are forecast independently, feature windows must be computed within the correct entity group and never bleed between entities.

### 6.3 Leakage-safe feature handling

Time-based features are a central risk. A conventional random split is prohibited. It is also insufficient to claim that a split is temporal if feature construction has already exposed validation or future data.

For every fold, verify that:

- lag values refer only to observations available before the predicted timestamp;
- rolling windows are backward-looking and do not include the current target unless that value would truly be known at prediction time;
- centered windows are not used;
- transforms, imputers, scalers, encoders, feature selectors, and similar learned steps are fitted on the fold’s training data only;
- sorting is explicit before any shift, rolling operation, or split;
- entity boundaries are respected; and
- rows whose historical windows are unavailable are handled consistently and documented.

The safest pattern is to place feature engineering and learned preprocessing inside a fold-aware pipeline or to recompute features using only information legitimately available at each fold boundary. If the repository’s precomputed feature approach is retained, the implementation must prove that every feature is strictly causal and cannot reference validation/future targets.

### 6.4 Learning curve

Generate a learning curve that shows training and validation error as the chronological training history grows.

Requirements:

- Use increasing chronological prefixes or another time-respecting scheme; do not randomly subsample observations.
- Evaluate both training and validation performance at each size.
- Use the chosen primary metric for the plotted curves, expressed consistently as error where lower is better.
- Include readable axis labels, a legend, a title, and enough context to identify the metric.
- Prefer uncertainty bands or error bars when fold-level variability is available.
- Save the final image under `data/eval/`.
- Reference and interpret the saved figure in the technical report.

The filename may follow repository conventions; otherwise use a descriptive name such as:

```text
data/eval/learning_curve.png
```

### 6.5 Model-fit diagnosis

Use both the learning-curve pattern and time-aware cross-validation evidence to classify the model as exactly one of:

- **Underfitting:** training and validation errors converge but remain high relative to business expectations/baseline performance.
- **Overfitting:** training error is substantially lower than validation error and the gap persists as training data grows.
- **Reasonably well fitted:** training and validation errors are both acceptably low, close to one another, and sufficiently stable.

There is no universal numerical threshold. The report must explain what “high,” “low,” “close,” and “stable” mean in this dataset’s units and business context. A label without evidence is not acceptable.

### 6.6 Corrective recommendation

The report must give a concrete next action consistent with the diagnosis and observed evidence.

Examples of diagnosis-to-action logic (illustrative, not automatic):

| Diagnosis | Appropriate direction | Inappropriate default response |
|---|---|---|
| Underfitting | Improve feature quality, revisit assumptions, or increase model capacity where evidence supports it | “Add more data” as the first response |
| Overfitting | Increase regularization, reduce unnecessary complexity/features, or add representative history | Increase model complexity |
| Reasonably well fitted | Recommend staging with stated monitoring/limitations, or address a specific unstable segment | Invent a problem or recommend arbitrary retuning |

The recommendation must name the specific model setting, feature family, data limitation, fold behavior, or error segment that motivates it. Avoid generic statements such as “optimize the model,” “get more data,” or “increase complexity.”

### 6.7 Technical report

Create:

```text
data/eval/evaluation_report.md
```

The report must be self-contained and include at least:

1. Executive diagnosis and staging recommendation.
2. Company/business context and the relative cost of error types.
3. Dataset scope, target, entities, forecast frequency, and temporal boundaries.
4. Existing model and relevant feature summary.
5. Cross-validation design, including fold count and leakage controls.
6. Fold-by-fold MAE and RMSE.
7. Mean ± standard deviation across folds for the chosen primary metric (and preferably both required metrics).
8. Training-versus-validation MAE and RMSE.
9. Learning-curve figure and interpretation.
10. Explicit classification: underfitting, overfitting, or reasonably well fitted.
11. Specific corrective action or promotion recommendation.
12. Limitations, remaining risks, and reproducibility notes.

Metric values must identify their units. The report must distinguish cross-validation validation results from the untouched final test set. It must not present test-set performance as cross-validation performance.

### 6.8 Tests

Add a focused unit test under:

```text
tests/pipelines/
```

At minimum, the test must prove that the temporal cross-validation strategy preserves chronological order for every fold. It should verify invariants such as:

- training indices/timestamps are ordered;
- validation indices/timestamps are ordered;
- the latest training timestamp is strictly earlier than the earliest validation timestamp (or follows an explicitly documented same-period grouping rule);
- validation windows move forward through time; and
- no future fold index appears in an earlier fold’s training sequence in a way that violates the chosen strategy.

Add focused regression tests for leakage-sensitive feature behavior if the implementation changes or introduces fold-specific feature generation. Use a small deterministic synthetic time series so failures are easy to understand. Follow existing test conventions and do not weaken existing tests.

## 7. Explicitly out of scope

Unless the repository’s existing implementation cannot be evaluated without a narrowly scoped repair, do not:

- build a brand-new forecasting model;
- replace the tuned model with a different algorithm;
- perform a new hyperparameter search;
- change the target definition or forecast horizon;
- redesign the monorepo or refactor unrelated pipelines;
- create a new frontend, dashboard, API, or deployment;
- promote or deploy the model to staging/production;
- alter production data, infrastructure, authentication, or CI beyond what the required test needs;
- use random `KFold`, shuffled splits, or the final test set for model selection;
- invent company names, field names, entity IDs, costs, thresholds, or metric results; or
- commit, push, merge, or open a pull request unless the user explicitly asks Cursor to do so.

## 8. Expected repository changes

The exact source filenames must follow existing repository conventions discovered during inspection. The minimum expected result is:

```text
<existing evaluation or pipeline module(s)>  # temporal CV, metrics, and learning-curve generation
data/eval/
├── evaluation_report.md
└── <learning-curve image>
tests/pipelines/
└── <focused temporal-CV test file>
```

Additional machine-readable evaluation output (for example JSON or CSV containing fold metrics) is encouraged when it improves reproducibility and aligns with repository conventions, but it is not a substitute for the Markdown report.

Dependencies must be added using:

```text
uv add <dependency>
```

Do not use `pip install` or Pipenv. Prefer existing dependencies and avoid adding a library for behavior already available in the project stack.

## 9. Recommended implementation sequence

1. Inspect repository instructions and the project memory bank.
2. Read the assigned company briefing and record the business error cost.
3. Trace the existing data, feature, model, and temporal-split pipeline end to end.
4. Reproduce the current baseline without changing model behavior.
5. Design fold boundaries over the training set and document leakage assumptions.
6. Add the chronological-order unit test first or alongside the splitter.
7. Implement leakage-safe fold evaluation with MAE and RMSE.
8. Produce fold-level results and mean ± standard deviation.
9. Generate and save the time-aware learning curve.
10. Interpret the combined evidence and select one diagnosis.
11. Write the technical report and specific recommendation.
12. Run focused tests, then applicable formatting, lint, type, and broader test checks.
13. Review every requirement and ensure generated artifacts are reproducible.

This sequence is guidance, not permission to ignore stronger repository-local instructions.

## 10. Validation expectations

Validation must be proportional to the implementation and use the project’s actual commands. At minimum, Cursor should:

- run the new focused test under `tests/pipelines/`;
- run existing tests covering the changed pipeline;
- run the project’s configured lint/format/type checks when applicable;
- execute the evaluation pipeline against the intended training data;
- confirm the learning-curve file exists and is readable;
- confirm the report contains real, reproducible metric values;
- manually inspect fold boundaries for temporal order and leakage risk; and
- record the exact commands and results in the project’s progress/memory documentation.

Do not claim a check passed unless it was run successfully. If data, credentials, services, or dependencies prevent full execution, report the exact limitation and clearly separate verified behavior from unverified behavior.

## 11. Acceptance criteria / definition of done

The project is complete only when all of the following are true:

- [ ] Work extends the existing company monorepo and existing forecasting model.
- [ ] Company-specific terminology, fields, IDs, and business costs match the assigned briefing.
- [ ] The original final test set remains isolated from cross-validation and diagnosis decisions.
- [ ] Temporal cross-validation uses at least five chronological, non-shuffled folds over training data.
- [ ] Fold boundaries and feature engineering are demonstrably free of future-data leakage.
- [ ] MAE and RMSE are calculated for training and validation.
- [ ] The primary metric is justified using business error costs.
- [ ] Cross-validation performance is reported as mean ± standard deviation.
- [ ] A time-aware learning curve is generated and saved under `data/eval/`.
- [ ] `data/eval/evaluation_report.md` explicitly diagnoses underfitting, overfitting, or reasonable fit.
- [ ] The diagnosis is supported by both learning-curve and cross-validation evidence.
- [ ] The corrective action or staging recommendation is specific and consistent with the diagnosis.
- [ ] A unit test under `tests/pipelines/` verifies chronological fold order.
- [ ] Required tests and applicable project checks pass, or exact external limitations are documented.
- [ ] No unrelated refactor, new product surface, deployment, or model replacement is introduced.

## 12. Handoff rules for Cursor

- Treat the repository and company briefing as the source of truth for all domain details.
- Make the smallest change that satisfies the assignment.
- Preserve existing user work and unrelated behavior.
- Search before creating new modules or abstractions.
- Do not hard-code metric values or conclusions; generate them from the real evaluation.
- Do not decide the diagnosis before seeing the results.
- Do not silently repair or replace missing prerequisite work; surface the blocker.
- Keep evaluation logic reproducible and separate from the untouched final test set.
- Update the repository’s project memory bank after material decisions, validation, or blockers, following the local `AGENTS.md` instructions.
- Do not commit, push, create a PR, merge, or deploy without explicit user authorization.

## 13. Key conceptual guardrail

The core deliverable is not a chart or a score in isolation. It is a defensible technical judgment that connects:

```text
chronological, leakage-safe evidence
        → model fit diagnosis
        → business interpretation
        → specific next action
```

If any link in that chain is missing, the evaluation is incomplete.
