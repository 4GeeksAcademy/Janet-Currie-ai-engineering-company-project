# HealthCore Data Pipeline Branch — Implementation Handoff

## Purpose and authority

This document is the implementation handoff for the **HealthCore data-pipeline branch**. A different agent will use it to plan and complete three dependent sprints in strict order. It records both the assignment requirements and the user's required working protocol.

The four linked 4Geeks documents are the assignment authority:

1. [HealthCore Business Performance Pipeline context](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/06-telemetry-data-pipelines/data-pipelines/CONTEXT-healthcore.md) — the company-specific source of truth for the entire branch.
2. [Part 1: Designing a Business Performance Data Pipeline](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-data-pipeline-design/README.md).
3. [Part 2: Implementing a Resilient Business Performance Pipeline](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-data-pipeline-build/README.md).
4. [Part 3: Pipeline Enhancement — Subflows and Tests](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-data-pipeline-enhancement/README.md).

When a generic example in a sprint brief differs from the HealthCore context, use the HealthCore context. Use the existing monorepo's conventions where the sources leave a choice open. Do not invent extra business requirements.

## Non-negotiable user instructions for the implementing agent

These workflow instructions are mandatory and override any temptation to combine work for speed:

1. Work in the user's existing HealthCore company-project monorepo, on a dedicated data-pipeline branch. Do not create a separate application or repository. If the branch name has not been provided, ask the user before creating it.
2. Complete the three sprints strictly in this order:
   1. pipeline design;
   2. pipeline build;
   3. pipeline enhancement.
3. **At the beginning of every sprint, create a detailed implementation plan and present it to the user for approval.** The plan must identify the exact files expected to change, data/schema implications, implementation steps, tests, validation commands, risks, assumptions, and sprint acceptance criteria.
4. **Do not build, scaffold, install dependencies, migrate data, or edit implementation files for a sprint until the user explicitly approves that sprint's plan.** Repository inspection and read-only analysis are allowed so the plan can be accurate.
5. Approval of one sprint applies only to that sprint. It is not approval to plan and implement all three at once.
6. Finish the approved sprint completely, validate it, report the results, and create its local commit before beginning the next sprint.
7. After each sprint commit, stop and obtain approval for the next sprint's newly prepared detailed plan. Do not implement later-sprint requirements early, even if touching the same files would be convenient.
8. Start each sprint from the latest committed state produced by the preceding sprint. Before planning or editing, inspect `git status`, recent commits, and the current files. Preserve unrelated user changes. Pull/fetch only when appropriate and safe; never discard local work to obtain a clean tree.
9. The user's instruction explicitly authorizes the three required local sprint commits after each sprint is complete and validated. It does **not** by itself authorize pushing, opening a pull request, merging, deploying, or changing production data. Obtain separate explicit permission for those external actions, even where a sprint's submission section mentions them.
10. Maintain the project-local `memory-bank/` throughout the implementation as required by the project's `AGENTS.md`. Read active memory and relevant implementation memory before substantial work; update it after material plans, decisions, milestones, validation, and handoffs.
11. Testing is part of each implementation sprint. Add focused tests for changed behavior and realistic edge cases, run the narrowest relevant checks first, and never claim a check passed unless it was actually run successfully.
12. Keep changes scoped. Do not refactor unrelated code, weaken tests, overwrite user work, expose secrets, or modify production infrastructure or data without explicit permission.

### Required sprint gate sequence

```text
Read current committed state
  -> write Sprint 1 detailed plan
  -> USER APPROVAL
  -> implement and validate Sprint 1 only
  -> commit Sprint 1
  -> read new committed state
  -> write Sprint 2 detailed plan
  -> USER APPROVAL
  -> implement and validate Sprint 2 only
  -> commit Sprint 2
  -> read new committed state
  -> write Sprint 3 detailed plan
  -> USER APPROVAL
  -> implement and validate Sprint 3 only
  -> commit Sprint 3
  -> final validation and handoff
```

If the user requests changes to a plan, revise the plan and wait for explicit approval. Silence, approval of this handoff, or approval of an earlier sprint is not approval to implement the current sprint.

## Business outcome

HealthCore operates 12 clinics across the US and UK. Dr. Okonkwo (CEO) and Claire (Chief Compliance Officer) need a board-ready **Monthly Clinic Supply Performance Report** by the first working day of each month. The pipeline must turn supply-chain telemetry into one monthly row per clinic so leadership no longer has to consolidate spreadsheets manually.

This pipeline serves non-technical business stakeholders. It is separate from the existing technical telemetry report used by engineering.

## Required KPIs and exact computations

| KPI | Source event | Required v1 computation |
| --- | --- | --- |
| Supply Cost per Clinic | `inbound_order_created` | Sum the event's supply cost for the clinic and calendar month. |
| Supply Consumption Volume | `outbound_order_created` | Count consumption events for the clinic and calendar month. Do not silently replace this with a sum of `quantity`. |
| Critical Stockout Frequency | `stock_threshold_triggered` | Count threshold-trigger events for the clinic and calendar month. |
| Expiry Risk Count | `supply_expiry_flagged` | Count expiry-flag events for the clinic and calendar month. |

Only these four event types feed v1. Do not add patient-level sources or widen the v1 KPI scope.

Before design or implementation, audit the already-completed telemetry schema. `inbound_order_created` must contain a cost value sufficient to compute `total_supply_cost`, such as `unit_cost` or `total_cost`. If it does not, the Sprint 1 plan must call out the smallest additive extension to that existing event type and define unambiguous calculation semantics. Do not create a new event type for cost and do not rewrite the technical telemetry report.

## Required aggregation contract

- Grain: one row per `clinic_id` per calendar month.
- `month_start`: first day of that month in UTC.
- Dimensions: `clinic_id`, `country`, `month_start`.
- `country`: `US` or `UK`.
- Computed fields: `total_supply_cost`, `supply_consumption_count`, `critical_stockout_count`, `expiry_risk_count`.
- Currency: `USD` for US clinics and `GBP` for UK clinics.
- Never convert or combine currencies. Cross-currency conversion is a v2 concern and is out of scope.
- Although the business description says consumption can be understood by department, the authoritative v1 destination table has clinic-month grain and no department column. Preserve `department` in source telemetry where applicable, but do not invent a department-grain destination or endpoint without user-approved scope expansion.
- Late events must be handled idempotently by recomputing/upserting the affected clinic-month window; generic sprint examples using daily partitions do not change HealthCore's required monthly grain.

## Required destination table

Create the destination under a dedicated `reporting` schema. The exact required table is:

```sql
create table reporting.monthly_clinic_supply_performance (
  id uuid primary key default gen_random_uuid(),
  clinic_id text not null,
  country text not null,
  month_start date not null,
  total_supply_cost numeric not null default 0,
  supply_consumption_count integer not null default 0,
  critical_stockout_count integer not null default 0,
  expiry_risk_count integer not null default 0,
  currency text not null,
  computed_at timestamptz not null default now(),
  unique (clinic_id, month_start)
);
```

The unique `(clinic_id, month_start)` key is the required basis for an idempotent upsert. `telemetry_events` is a read-only source for this pipeline and must never be used as its destination.

## Required reporting API

Implement these endpoints in a new `services/reporting/` module, separate from `services/telemetry/`:

- `GET /reporting/monthly-clinic-supply-performance`
  - accepts an optional `month_start`;
  - defaults to the most recent computed month;
  - returns every clinic for the selected month;
  - exposes the exact KPI and currency fields from the HealthCore contract.
- `GET /reporting/pipeline-runs/latest`
  - returns status and metadata for the latest run.
- `POST /reporting/pipeline-runs`
  - triggers a manual pipeline run.

The reporting service may call/import pipeline functions or flows; it must not duplicate ETL logic. Follow the existing API's authentication, routing, error, and response conventions. The source does not prescribe whether manual execution is synchronous or asynchronous, so Sprint 1 must design this consistently with the existing application and include the decision in the plan for approval.

Expected KPI response shape:

```json
{
  "month_start": "2026-07-01",
  "clinics": [
    {
      "clinic_id": "austin-north",
      "country": "US",
      "total_supply_cost": 18420.50,
      "supply_consumption_count": 340,
      "critical_stockout_count": 1,
      "expiry_risk_count": 4,
      "currency": "USD"
    }
  ]
}
```

## Privacy and scope boundaries

- This is an aggregate supply-chain pipeline only.
- No table, endpoint, dashboard, log, exception, cache, fixture, or evaluation artifact may contain patient identifiers, diagnoses, or real or simulated PHI.
- Aggregate by clinic (and retain department only in allowed source-event context), never by patient.
- Respect HIPAA and UK GDPR.
- Do not join patient-level tables.
- Do not modify `services/telemetry/analysis.py`.
- Do not modify the behavior or contract of `GET /telemetry/report`.
- Do not write pipeline results back to `telemetry_events`.
- Do not replace or repurpose the technical telemetry system.
- Additive changes to an existing mandatory telemetry event are allowed only when required for the HealthCore pipeline, such as the missing inbound-order cost value, and must be approved in the relevant sprint plan.

## Sprint 1 — Pipeline design

### Plan gate

Before editing deliverables, inspect the actual monorepo, its `AGENTS.md`, memory bank, current telemetry implementation/schema, data folders, API conventions, database/migration conventions, test setup, and dependency tooling. Then give the user a detailed Sprint 1 plan and wait for explicit approval.

### Deliverable

Create and commit:

```text
data/pipelines/PIPELINE_DESIGN.md
```

This sprint is design-first. Do not write Prefect orchestration or reporting endpoints. If the telemetry cost field is missing, include the required additive schema change explicitly in the plan; make it only after approval and keep it separate from the technical report path.

### Required design contents

1. **Current state and business gap**
   - existing telemetry events and their storage;
   - what the engineering-facing technical report already answers;
   - why it does not answer the Monthly Clinic Supply Performance Report business need.
2. **One-sentence pipeline purpose**
   - name the monthly deliverable, Dr. Okonkwo/Claire audience, four KPIs, and source metrics.
3. **Extraction contract**
   - `telemetry_events` payload/envelope shape, relevant event types, update behavior, cadence, filters, and any justified existing domain tables;
   - verify the cost field and define whether cost is already total or must be calculated from unit cost and quantity.
4. **Data flow diagram**
   - text or Mermaid with at least extraction, transformation, and load;
   - use real HealthCore entities and table names.
5. **Transformation contract**
   - UTC month boundaries, grouping, event counting, cost calculation, currency handling, malformed data policy, duplicates, and late-arriving events.
6. **Destination and API contract**
   - exact reporting table and all three reporting endpoints;
   - explicitly separate these from technical telemetry.
7. **Idempotency and concurrency**
   - source deduplication using `eventId` where applicable;
   - clinic-month upsert on `(clinic_id, month_start)`;
   - deterministic recovery after partial load;
   - recomputation for late events;
   - prevention/handling of overlapping scheduled and manual runs.
8. **Observability and recovery**
   - run record/control structure with, at minimum, `run_id`, start time, end time, records processed, final status, and captured errors, including concrete data types and audit rationale;
   - checkpoints, source window, output counts, and event-to-run correlation sufficient to distinguish zero activity from pipeline silence and to resume safely.
9. **Prefect mapping**
   - at least one concrete main flow and three concrete tasks for extract, transform, and load;
   - relevant states (`Running`, `Completed`, `Failed`);
   - external configuration/credentials represented as Prefect blocks;
   - intended monthly schedule and CLI command;
   - name tasks and flows with HealthCore domain vocabulary, not generic `extract_data` labels.
10. **Application integration design**
    - each endpoint's request/response/error behavior and the `data/pipelines/` function or flow it calls;
    - no ETL logic in `services/`.
11. **Answers to resilience questions**
    - duplicate events, reruns after partial loads, late events, zero activity versus capture failure, traceability, volume swings, database outage recovery, offline browser buffering, transmission retry/idempotency keys, and concurrent runs;
    - distinguish required Sprint 2 work from optional Sprint 3 enhancements.
12. **Testing and validation strategy**
    - unit, integration, idempotency, failure/retry, API, CLI, and dashboard contract checks planned for later sprints.

### Sprint 1 acceptance criteria

- `PIPELINE_DESIGN.md` is readable, HealthCore-specific, and consistent with the source-of-truth context.
- Every required stage, KPI, field, table, endpoint, resilience property, and boundary above is covered.
- The execution log specifies at least five required fields with types and justifications.
- At least one main Prefect flow and three tasks are concretely named.
- The document plans all three reporting endpoints and identifies their pipeline dependencies.
- No Prefect pipeline, reporting service, or dashboard has been built early.
- Documentation checks and any approved schema validation pass.
- The completed sprint is committed before Sprint 2 planning begins. The assignment's requested message is:

```text
feat: add business performance pipeline design document
```

## Sprint 2 — Build the resilient pipeline

### Plan gate

Do not begin Sprint 2 automatically after the Sprint 1 commit. Re-read the committed `PIPELINE_DESIGN.md`, current code, memory bank, and HealthCore context. Produce a new detailed Sprint 2 implementation plan based on the actual approved design and present it to the user. Wait for explicit approval.

### Required implementation

- Add Prefect 3 using the repository's actual dependency workflow (`prefect>=3`). Do not assume `uv` if the monorepo uses another established tool; explain any divergence from the sprint's sample command.
- Implement `data/pipelines/pipeline.py` with a main Prefect flow and at least three independent `@task` stages with explicit inputs/outputs: HealthCore-specific extraction, transformation, and load.
- Read relevant rows from `telemetry_events` without modifying the source.
- Transform exactly the four HealthCore KPIs at clinic-month grain.
- Load by idempotent upsert into `reporting.monthly_clinic_supply_performance` using `(clinic_id, month_start)`.
- Add retries and `retry_delay_seconds` to every external-service task; justify the chosen retry policy in a comment.
- Add Prefect caching (`cache_key_fn`, `cache_expiration`) to at least one expensive transformation. The requirement is that a valid recent result need not repeat within one hour; document the cache-key inputs and validity period.
- Add at least one genuinely optional/non-critical step and invoke it with `return_state=True`; its failure must be recorded without preventing successful core extract-transform-load completion.
- Explicitly handle at least one task state/failure with `return_state=True`.
- Record every pipeline run's start, end, records processed, status, and errors in the approved database control table or structured log. Include `run_id` and processing window if designed in Sprint 1.
- Preserve a CLI entry point so `python data/pipelines/pipeline.py` invokes the full flow.
- Implement all three endpoints in `services/reporting/`, reusing pipeline functions/flows and existing API conventions.
- Add any required reporting schema migration and focused automated tests in the repository's established locations.

### Required validation

At minimum, and adjusted to the actual repo:

- focused transformation tests;
- reporting endpoint tests;
- migration/schema validation;
- a twice-over-the-same-window idempotency test proving identical final rows and no duplicates;
- retry/optional-failure behavior checks;
- relevant lint/type checks;
- `python data/pipelines/pipeline.py` against a safe test/local configuration.

Never run against production data or infrastructure without explicit permission. If credentials or services prevent a real CLI/integration run, report the exact limitation and perform the best safe substitute; do not claim the full run passed.

### Sprint 2 acceptance criteria

- `data/pipelines/pipeline.py` exists with the required flow/tasks, retries, cache, optional failure tolerance, run metadata, idempotent load, and CLI entry point.
- The reporting table/migration and all three reporting endpoints match the approved design and HealthCore contract.
- Existing technical telemetry remains unchanged.
- Focused tests and safe validation have actually run with recorded results.
- The completed sprint is committed before Sprint 3 planning begins. The assignment's requested message is:

```text
feat: implement resilient business performance pipeline
```

## Sprint 3 — Subflows, tests, and business dashboard

### Plan gate

Do not begin Sprint 3 automatically after the Sprint 2 commit. Inspect the committed, working Part 2 implementation and its validation results. Produce a new detailed Sprint 3 plan covering the refactor, tests, dashboard integration, regression risks, and validation. Present it to the user and wait for explicit approval.

### Required implementation

1. **Refactor to subflows**
   - keep the main flow as coordinator;
   - create at least three independently executable `@flow` subflows for HealthCore-specific extraction, transformation, and load;
   - give every subflow explicit inputs and outputs; do not communicate through global variables;
   - move optional steps into subflows where appropriate and preserve `return_state=True` behavior;
   - use domain-specific names tied to clinic supply performance, not generic names such as `extract_data`.
2. **Unit tests**
   - create `tests/pipelines/test_pipeline.py`;
   - include at least three isolated transformation-task tests using in-memory telemetry-shaped fixtures and no database/API dependency;
   - cover all four KPI computations across the suite, even though the assignment minimum is three tests;
   - include malformed/invalid input behavior;
   - include at least one hand-calculated KPI assertion;
   - include realistic boundaries such as empty input, duplicate event IDs, month boundaries/late events, country/currency separation, and missing/invalid cost where applicable.
3. **Preserve CLI behavior**
   - `python data/pipelines/pipeline.py` must still run the complete ETL after the refactor; preserve rather than rebuild the Part 2 entry point.
4. **Business dashboard**
   - add a reporting page under `uis/backoffice/` using the existing frontend's routing, component, data-fetching, authentication, loading, empty, and error-state conventions;
   - fetch the Part 2 KPI endpoint; do not query the database directly from the UI;
   - display every required KPI with its exact business label and reporting month;
   - keep USD and GBP values visibly separate and never show a cross-currency total;
   - make the result legible to Dr. Okonkwo and Claire without requiring technical interpretation;
   - visual polish is secondary to correct, accessible, clearly labeled real data.
5. **Optional approved enhancements**
   - implement only enhancements actually prioritized in the approved design, such as a heartbeat/silence signal, overlapping-run lock, or idempotency-key behavior;
   - note in `PIPELINE_DESIGN.md` which design question each enhancement answers and why it was prioritized;
   - do not invent optional work just to expand scope.

### Required validation

- `python -m pytest tests/pipelines/test_pipeline.py` passes.
- Existing and added reporting/API tests pass.
- `python data/pipelines/pipeline.py` completes safely in the authorized environment after the refactor.
- The main flow demonstrably invokes at least three subflows with explicit contracts.
- Dashboard tests/build/type/lint checks appropriate to the frontend pass.
- Perform a safe dashboard smoke check for loading, populated, empty, and error states.
- Reconfirm idempotency, privacy boundaries, monthly grain, currency separation, and non-regression of technical telemetry.

### Sprint 3 acceptance criteria

- The flow topology, isolated unit tests, preserved CLI, and required dashboard all meet the source rubric.
- All four KPI labels and values are sourced from the reporting API and are understandable to business users.
- No patient data or cross-currency aggregation is introduced.
- Actual validation results and any unverified risks are recorded.
- The completed sprint is committed. The assignment's requested message is:

```text
feat: refactor business performance pipeline into subflows, add unit tests, and add reporting dashboard
```

The source asks for a push and pull request after Part 3, but this handoff does not grant that permission. Ask the user before pushing or opening a PR.

## Implementation decisions that must be made from repository evidence

The sources intentionally leave some implementation details open. The implementing agent must inspect the monorepo, propose them in the applicable sprint plan, and obtain approval rather than guessing:

- exact dedicated branch name;
- existing telemetry cost-field availability and the precise `total_supply_cost` formula;
- reporting-schema migration mechanism and database client pattern;
- `pipeline_runs` storage schema, checkpoint design, and status vocabulary;
- scheduled-run mechanism and exact time/timezone needed to meet the first-working-day cadence;
- synchronous versus asynchronous manual-run endpoint behavior and concurrency lock;
- invalid-event quarantine/skip/fail policy;
- source extraction window and late-arrival lookback;
- Prefect block names and secret/config management;
- frontend route/file names and visual components consistent with `uis/backoffice/`;
- test commands, dependency commands, and application wiring dictated by the actual repository.

These choices may refine implementation mechanics but may not change the four KPIs, monthly clinic grain, destination table, reporting endpoints, privacy boundary, or sprint gates without explicit user approval.

## Final branch completion checklist

- [ ] Sprint 1 plan was explicitly approved before Sprint 1 edits.
- [ ] Sprint 1 is complete, validated, and committed.
- [ ] Sprint 2 plan was prepared from the committed Sprint 1 state and explicitly approved before Sprint 2 edits.
- [ ] Sprint 2 is complete, validated, and committed.
- [ ] Sprint 3 plan was prepared from the committed Sprint 2 state and explicitly approved before Sprint 3 edits.
- [ ] Sprint 3 is complete, validated, and committed.
- [ ] The implementation produces the four required clinic-month KPIs in the exact reporting table.
- [ ] All three reporting endpoints work and the dashboard uses the KPI endpoint.
- [ ] Idempotency, retries, caching, failure tolerance, run observability, subflows, CLI execution, and tests meet the rubrics.
- [ ] Technical telemetry behavior remains intact.
- [ ] HIPAA/UK GDPR constraints and currency separation are preserved everywhere.
- [ ] Project memory records the final architecture, contracts, decisions, tests, and limitations.
- [ ] No push, PR, merge, deployment, or production-data change occurred without separate explicit permission.

