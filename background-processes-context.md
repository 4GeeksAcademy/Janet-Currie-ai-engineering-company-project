# HealthCore Background Processes Branch — Implementation Handoff

## Purpose

This document is the execution context for the **background-processes branch** of the existing HealthCore company-project monorepo. The implementation agent must add one independently scheduled nightly process that backs up the previous UTC day's telemetry to CSV, triggers the already-built data pipeline, and records the orchestration outcome in the database.

This handoff is documentation only. No branch, migration, script, service, cron entry, scheduler container, dependency, test, commit, push, pull request, or deployment was created while preparing it.

## Authoritative source

- [4Geeks Academy — Background Processes](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-cronjobs/README.md)

The assignment was reviewed on October 21, 2026. If it conflicts with newer instructor direction, follow the newer requirement and record the difference. Where the assignment leaves an implementation choice open, follow the checked-out monorepo's established database, migration, logging, configuration, dependency, and testing conventions.

## Required starting point and repository inspection

Implement this work in the user's existing company-project monorepo, not in this documentation-only context workspace and not in a new repository. The correct base must already contain both prerequisites:

1. the telemetry implementation and its `telemetry_events` table; and
2. the completed Milestone 6 business-performance pipeline, including its executable CLI and `pipeline_runs` tracking.

Before proposing edits, inspect:

- repository-level and directory-level `AGENTS.md` files;
- active `memory-bank/` files and relevant implementation memory;
- current branch, recent commits, remotes, and working-tree changes;
- the telemetry event model, timestamp field, database schema, and storage code;
- the actual pipeline package, CLI entry point, accepted arguments, working-directory assumptions, environment needs, and exit behavior;
- the `pipeline_runs` implementation so it is not duplicated or repurposed;
- database/SQLModel/session factories, migrations, transaction patterns, and test fixtures;
- configuration and secret-loading conventions;
- logging conventions and CLI/script patterns;
- Docker Compose or deployment topology if a scheduler container is being considered; and
- the current test, lint, type-check, and migration-validation commands.

Do not assume paths from this handoff exist unchanged in the implementation checkout. Use repository evidence. Preserve unrelated user changes and do not refactor surrounding systems unless required for this ticket.

## Ticket and business outcome

Implement **Ticket #DEV-53 — Nightly Telemetry Script**.

HealthCore's telemetry and data pipeline already exist, but pipeline operation currently depends on a person. The required background process must run nightly without API involvement and:

1. select the previous calendar day's telemetry in UTC, unless an explicit test date is supplied;
2. create a CSV backup in `data/raw/` only when that day's file does not already exist;
3. invoke the existing data pipeline as a separate subprocess;
4. record the orchestration lifecycle and outcome in `job_runs`; and
5. prevent both overlapping execution and repeat processing of the same target date.

The expected operator outcome is a traceable nightly job that is safe to retry, produces an audit/recovery snapshot, and never leaves an ordinary caught failure recorded as successful or indefinitely `processing`.

## Architecture boundaries

### Independent from FastAPI

The nightly job must be an independent operating-system process. It may reuse repository database/configuration modules that are safe outside the web server, but it must not be scheduled or executed on FastAPI's main thread.

Forbidden trigger mechanisms include:

- FastAPI lifespan startup hooks;
- `APScheduler` embedded in the API process;
- `@repeat_every` in the API process; and
- an endpoint request that performs the nightly work inline.

An OS crontab or a dedicated scheduler container/process is acceptable. A dedicated worker is acceptable only when it remains independent of the API process.

### `job_runs` and `pipeline_runs` are different

Do not merge, alias, or replace these records:

| Record | Layer | Responsibility |
| --- | --- | --- |
| `job_runs` | Nightly orchestration added here | CSV backup, subprocess trigger, global overlap guard, per-date idempotency, and overall job outcome |
| `pipeline_runs` | Existing Milestone 6 ETL | Extract/transform/load phases, watermarks/checkpoints, source/output counts, and internal pipeline outcome |

The nightly script owns one `job_runs` lifecycle. The invoked pipeline continues to own its own `pipeline_runs` record. Where practical, logs may include both identifiers for correlation, but the tables must retain separate responsibilities.

### CSV is backup output, not pipeline input

The CSV is an audit and recovery snapshot of `telemetry_events`. The existing pipeline must continue reading from the database using its established SQL/window/watermark behavior. Do not change the pipeline to consume `data/raw/telemetry_YYYY-MM-DD.csv`.

### HealthCore privacy boundary

The project operates across US and UK clinics and must preserve its HIPAA/UK GDPR boundary. Export only the already-approved telemetry envelope and allowlisted event properties needed by the telemetry system. Never add patient identifiers, diagnoses, medical-record data, credentials, JWTs, raw authorization data, or secrets to CSV files, logs, job metadata, fixtures, or exception text.

## Required deliverables

The exact paths must follow the real monorepo, but the branch must contain the equivalent of:

```text
scripts/nightly_export.py
services/<established-location>/job_runner.py
<database migration or schema update for job_runs>
<focused unit and integration tests>
<cron or scheduler-container configuration>
<operator/PR documentation for schedule and evidence>
```

The assignment names `scripts/nightly_export.py` and requires status logic under `services/`. Keep those boundaries unless the actual checkout proves a minor import/package adjustment is needed. Do not bury status transitions inside the script or copy ETL logic into the service.

## `job_runs` data contract

Create a persistent `job_runs` table with at least:

| Field | Required semantics |
| --- | --- |
| `id` | Stable primary key using the repository's normal identifier type |
| `job_name` | For this process, exactly `nightly_export` |
| `target_date` | Required calendar date identifying the UTC day being processed |
| `status` | Constrained to `pending`, `processing`, `completed`, or `failed` |
| `started_at` | UTC timestamp set when execution actually begins |
| `finished_at` | UTC timestamp set for `completed` and `failed`; null before a terminal state |
| `error_message` | Null for normal success; safe diagnostic text for failure |
| `created_at` | UTC creation timestamp |

Required database behavior:

- add an index on `(job_name, target_date)` for the per-date completion lookup;
- use a database constraint or the repository's equivalent validation to prevent invalid status values;
- keep all persisted timestamps timezone-aware and normalized to UTC; and
- make schema creation reproducible through the existing migration/schema workflow.

### Concurrency must be atomic

The assignment defines an existing `processing` row for `nightly_export` as the distributed lock. Do not create a lock table, lock column, file lock, Redis lock, or database advisory lock.

A check followed by an unprotected insert/update is race-prone: two processes can both observe no active row. Use the smallest database-native atomic design compatible with the actual database. A recommended design is a partial unique database index that allows at most one row where `job_name = 'nightly_export'` and `status = 'processing'`, combined with a transaction and graceful handling of the uniqueness conflict. This is enforcement of the required status-based lock, not a second lock mechanism.

If the actual database/migration tooling requires another atomic conditional transition, document and test it. In-memory or process-local mutexes are insufficient because separate cron processes do not share memory.

## Required state machine

Every eligible run follows this lifecycle:

```text
pending -> processing -> completed
                      -> failed
```

- Create `pending` before work starts.
- Transition to `processing` immediately before export/pipeline work and set `started_at`.
- Transition to `completed` only after all required work succeeds and set `finished_at`.
- Catch execution exceptions, persist `failed`, a safe error message, and `finished_at`, log the error, and return a non-zero process exit.
- Never mark a pipeline failure as completed.
- Never leave an ordinary caught export, subprocess, database, or serialization failure in `processing`.
- Commit transitions deliberately so operators and competing processes observe accurate state.

Hard termination such as `SIGKILL`, host loss, or a database outage during the final update cannot be repaired by Python `finally` alone. Do not invent an unrequested second lock. Document this operational limitation and any repository-supported recovery procedure; propose stale-run recovery separately if the user wants it.

## Startup decision order

Implement the order transactionally enough to preserve concurrency safety:

1. initialize CLI logging;
2. resolve and validate `target_date`;
3. check for any `processing` `nightly_export` run, regardless of target date;
4. if one exists, log an informational blocked/cancelled event and exit successfully without creating work;
5. check for a `completed` row for `(nightly_export, target_date)`;
6. if one exists, log an informational duplicate skip and exit successfully without exporting or invoking the pipeline;
7. create the new `pending` row;
8. atomically acquire the required status lock by moving that row to `processing`;
9. export the target date if its final CSV is absent;
10. invoke the pipeline exactly once;
11. transition this run to `completed`; or, on error, transition it to `failed` and exit non-zero.

Concurrency may change the world between steps 3 and 8. The database-enforced processing constraint/conditional transition is authoritative. Losing that race must be treated like the blocked path: log it and abort silently without doing work. Clean up or terminally resolve any newly created `pending` row according to the approved schema/service design; do not leave a meaningless pending zombie.

Skipped invocations should reuse the existing row's status in logs: `processing` for an overlap and `completed` for an already-finished date. The assignment does not define a `skipped` database status, so do not expand the enum merely to model an invocation that intentionally created no new run.

## Target-date contract

- Read optional `TARGET_DATE` in exact `YYYY-MM-DD` form.
- Reject malformed or impossible dates before creating a run.
- When absent, calculate the previous calendar date in UTC, not local/server time:

```python
datetime.now(timezone.utc).date() - timedelta(days=1)
```

- Do not use “last 24 hours”; use the half-open UTC calendar window `[target_date 00:00:00Z, target_date + 1 day 00:00:00Z)`.
- Keep a date/time provider injectable or patchable so boundary tests do not depend on the wall clock.
- Confirm which timestamp column represents event occurrence. Prefer the established event timestamp contract; do not silently substitute ingestion or update time.

## CSV export contract

Write to:

```text
data/raw/telemetry_YYYY-MM-DD.csv
```

Required behavior:

- create `data/raw/` if absent, using a repository-safe relative path resolved from the repository root rather than the caller's current directory;
- query only `telemetry_events` whose event timestamp falls inside the target UTC day;
- preserve a deterministic column order and deterministic row ordering, normally by event timestamp and stable event ID;
- include a header even if the day has zero events, so an empty successful snapshot is distinguishable from no export;
- serialize timezone-aware timestamps consistently, preferably ISO 8601 UTC;
- serialize structured properties in a stable, valid form consistent with the established telemetry contract;
- never expose fields outside the approved telemetry export boundary;
- if the final file already exists, do not rewrite, append, duplicate, or truncate it;
- write a new export through a temporary file in the same directory and atomically rename it only after success, so a crash cannot leave a final-looking partial CSV; and
- remove only the temporary file created by the current failed attempt. Never delete or overwrite an unfamiliar final export.

The existence check is a file-level safeguard, while the completed `job_runs` lookup is the orchestration idempotency guarantee. If a prior failed run produced the final CSV but the pipeline failed, the retry must reuse the CSV and retry the pipeline.

## Pipeline subprocess contract

After the export exists, invoke the existing Milestone 6 pipeline as a child process. The assignment gives this reference only:

```bash
python -m data.pipelines.telemetry_kpi_daily.run --no-prefect
```

The previous HealthCore pipeline handoff instead required a CLI around `data/pipelines/pipeline.py`. Inspect the implemented branch and use its real supported entry point; do not create a duplicate pipeline or assume the reference path exists.

Subprocess requirements:

- use the current Python interpreter (`sys.executable`) rather than assuming `python` resolves to the same environment;
- pass arguments as a list without `shell=True`;
- run from the verified repository root;
- preserve required environment/configuration without logging secrets;
- propagate only a supported target/window argument if the pipeline actually exposes one—do not invent CLI semantics;
- treat a non-zero exit as a job failure;
- keep subprocess output visible or capture and log it safely according to repository conventions; and
- include enough context to correlate the nightly job with the pipeline run without merging their state models.

The nightly job's target date controls the CSV backup and per-day idempotency. The pipeline retains its own approved watermark/window behavior unless its existing CLI explicitly allows a target date.

## `job_runner` service contract

Implement status control in a service module under the real `services/` package. The script should orchestrate through this module instead of writing status SQL inline.

At minimum provide repository-idiomatic equivalents of:

- `create_job_run(job_name, target_date)`;
- `mark_processing(run_id, started_at)` with atomic overlap protection;
- `mark_completed(run_id, finished_at)`;
- `mark_failed(run_id, finished_at, error_message)`;
- `has_processing_lock(job_name)`; and
- `has_completed_for_date(job_name, target_date)`.

Interfaces may accept an explicit database session/unit-of-work if that is the established pattern. Keep transactions and session ownership explicit. Query helpers should return typed records or booleans, not leak unrelated ORM state.

Only valid transitions are allowed. A terminal run must not return to `processing`, and a different run must not be updated accidentally. Apply the smallest compare-and-set/status predicate needed to prevent invalid concurrent transitions.

## Idempotency invariants

For `job_name = 'nightly_export'`:

1. At most one run may be `processing` across all target dates.
2. At most one successful orchestration is needed for a given `target_date`.
3. If a completed run exists for that date, a new invocation performs no export and launches no pipeline.
4. A failed run may be retried for the same date.
5. A retry must reuse an already-present final CSV and may invoke the pipeline again because the previous orchestration did not complete.
6. Two concurrent invocations must result in only one export/pipeline execution.
7. Pipeline-internal idempotency remains the responsibility of the existing pipeline and its `pipeline_runs`/destination-upsert design.

A unique constraint for successful `(job_name, target_date)` rows is advisable when supported, because application-only duplicate checks are race-prone. If added, keep it compatible with retaining failed history for the same date.

## Trigger and deployment decision

Choose exactly one independent trigger based on the actual deployment model:

### OS crontab

Appropriate when the application runs on a stable host with managed cron and direct access to the repository/runtime. The entry must set an explicit working directory, executable/virtual-environment path, configuration source, and log destination. Do not rely on an interactive shell's `PATH`.

### Dedicated scheduler container

Appropriate when the monorepo is deployed with Compose/containers. It must use the same versioned code and required database configuration, mount or persist `data/raw/` appropriately, and run independently from the API container. Do not add a second API server merely to schedule the job.

The implementation agent must choose and justify the method from repository/deployment evidence. Define the schedule in UTC explicitly. If the product owner has not supplied a time, propose a low-traffic default such as `02:00 UTC` (`0 2 * * *`) and obtain confirmation before treating it as an operational commitment.

Configuration or documentation should show:

- exact cron expression and timezone;
- exact command and working directory;
- environment/configuration loading;
- where logs and CSVs persist;
- how to run manually with `TARGET_DATE`;
- how to inspect `job_runs` and `pipeline_runs`; and
- how to retry a failed date safely.

Do not modify production crontab, deployment infrastructure, production data, or credentials without explicit permission. A version-controlled example/configuration and local safe validation are sufficient until deployment is authorized.

## Logging and observability

Use the established structured logging setup. Log `INFO` for start, status transitions, CSV created/reused, pipeline start/finish, duplicate skip, overlap block, and successful finish. Log `ERROR` for failures.

Every relevant log event must include:

- UTC timestamp;
- `job_name` (`nightly_export`);
- resulting/current status;
- `target_date` when known;
- `job_run_id` when one exists; and
- a concise event/reason.

Never log database URLs, passwords, tokens, raw authorization data, patient data, entire telemetry payloads, or unbounded subprocess output. Persist a useful but bounded/sanitized error message in `job_runs`; full tracebacks belong in protected process logs.

Use process exit codes consistently:

- `0` for completed, already-completed duplicate, or overlap-aborted invocation;
- non-zero for invalid configuration/date or a failed eligible run.

## Error-handling requirements

Test and correctly classify failures from:

- database connection/query/commit;
- target-date parsing;
- output-directory or file permissions;
- CSV serialization;
- partial temporary-file writes;
- missing pipeline module or wrong working directory;
- pipeline timeout, termination, or non-zero exit; and
- failure while persisting the terminal status.

The broad orchestration boundary must attempt `mark_failed` for any exception after a run enters `processing`, while preserving the original exception for logs and process exit. If the database itself prevents the failure update, log both the original error and the status-persistence failure without claiming the row was repaired.

Do not catch `BaseException` indiscriminately. If graceful signal handling is added, keep it narrow, ensure it does not mislabel a still-running child, and test it.

## Required test coverage

Follow the existing test layout and fixtures. Add focused tests for observable behavior, not implementation trivia.

### Date resolution

- no override returns yesterday in UTC;
- valid `TARGET_DATE` is accepted;
- malformed and impossible dates fail before work begins;
- month-end, year-end, and leap-day boundaries are correct.

### Job service and state machine

- eligible run moves `pending -> processing -> completed` with correct timestamps;
- export or subprocess failure moves `processing -> failed`, records safe error text, and sets `finished_at`;
- terminal states cannot transition illegally;
- completed lookup is scoped by both job name and target date;
- processing lookup is global to the job name, not target date;
- failed runs remain available as history and can be retried.

### Idempotency and concurrency

- a completed date skips both export and subprocess;
- an existing processing run exits quietly;
- two concurrent process-level invocations result in one winner and one blocked invocation;
- no race leaves an extra `pending` or two `processing` rows;
- a failed run with an existing CSV reuses the file and retries the pipeline;
- repeat execution produces no duplicate final CSV or pipeline execution after completion.

Do not replace the concurrency test with two sequential function calls. Exercise the database behavior with separate processes/connections where the test environment supports it.

### CSV export

- only events inside `[day_start, next_day_start)` are exported;
- boundary timestamps at exactly midnight are classified correctly;
- output name, headers, encoding, stable order, and serialization are correct;
- zero-event days produce a valid header-only snapshot;
- an existing final file remains byte-for-byte unchanged;
- failure does not expose a partial final file;
- sensitive/unapproved fields are absent.

### Subprocess and CLI

- successful child exit completes the job;
- non-zero child exit fails the job and produces a non-zero parent exit;
- the verified CLI can run as `python scripts/nightly_export.py` from the documented environment;
- command construction avoids a shell and uses the correct interpreter/root;
- logs include required context without secrets.

### Regression checks

Run the narrow job tests first, then the relevant database/migration, telemetry, pipeline, lint, type, and broader backend suite. Confirm the API starts and handles requests normally without importing or starting the scheduler. Use only local/test data unless a different environment is explicitly authorized.

## Manual validation scenarios

Use a safe test database and a known `TARGET_DATE`:

1. successful first run creates one CSV, one completed `job_runs` record, and one corresponding pipeline run;
2. identical second run logs a duplicate and changes neither CSV nor pipeline output/run count;
3. two simultaneous invocations yield one worker and one silent/INFO-level cancellation;
4. forced export failure produces `failed` with no final partial CSV;
5. forced pipeline non-zero exit produces `failed` while preserving the completed CSV for retry;
6. retry of the failed date reuses the CSV and can complete;
7. timestamps, statuses, target date, errors, and cross-table correlation are queryable;
8. FastAPI remains responsive and contains no embedded scheduler.

Record actual commands and results. Never claim concurrency, idempotency, failure recovery, or migration behavior passed unless those scenarios were actually exercised.

## Documentation and submission evidence

The eventual pull request body must include:

- chosen trigger and short justification;
- cron expression and timezone;
- sample successful log;
- sample failed or overlap-blocked log;
- generated CSV filename and a safe first-rows excerpt or screenshot;
- migration and validation commands/results; and
- explicit explanation that CSV is a backup while the pipeline reads the database.

The assignment also requires the `cronjob` label and a PR into `main`, followed by merge when approved. These source instructions do not override repository authorization rules: do not commit, push, open/label/merge a PR, or deploy unless the user explicitly authorizes those actions. Preserve the evidence locally so it is ready when authorized.

## Out of scope

- changing telemetry event semantics or adding patient-level telemetry;
- changing the four HealthCore business KPIs or reporting dashboard;
- making CSV the pipeline source;
- merging `job_runs` and `pipeline_runs`;
- a general queue/Celery architecture (covered by later message-queue work);
- embedded FastAPI scheduling;
- a second lock table/flag/service;
- production deployment or production data changes without permission;
- unrelated refactors; and
- broad observability infrastructure beyond the required logs and run records.

## Decisions the implementation agent must derive from the checkout

Do not guess these in advance:

- the correct base branch and new branch name;
- actual database engine(s), session API, model type, migration tool, and schema namespace;
- exact `telemetry_events` timestamp and property serialization fields;
- actual data-pipeline CLI and whether it supports a target-date/window argument;
- repository-root discovery and import strategy for direct script execution;
- location of the service module inside the real monorepo;
- partial-index/conditional-transition syntax supported by the deployed and test databases;
- error-message size and sanitization convention;
- log format and destination;
- whether OS cron or a scheduler container fits the deployment topology;
- final UTC execution time; and
- exact test, lint, type-check, migration, and smoke-test commands.

Document each material decision and its evidence in the project memory bank and eventual PR description.

## Completion checklist

- [ ] Work is based on the branch containing both telemetry and the completed Milestone 6 pipeline.
- [ ] `job_runs` exists with every required field, valid statuses, UTC timestamps, and `(job_name, target_date)` index.
- [ ] `job_runs` remains distinct from `pipeline_runs`.
- [ ] `scripts/nightly_export.py` runs directly from the documented CLI environment.
- [ ] Default target is yesterday in UTC and `TARGET_DATE=YYYY-MM-DD` works.
- [ ] CSV contains only the target UTC day's approved telemetry and is a backup, not pipeline input.
- [ ] Existing CSVs are not overwritten and partial files are not exposed as final files.
- [ ] Existing data pipeline is invoked through its verified CLI exactly once for an eligible run.
- [ ] State transitions are `pending -> processing -> completed | failed` with accurate timestamps/errors.
- [ ] The `processing` status is the only distributed-lock state and acquisition is atomic.
- [ ] Completed `(nightly_export, target_date)` runs are skipped idempotently.
- [ ] Two simultaneous real processes produce one worker and one blocked invocation.
- [ ] Caught failures do not leave the run in `processing`.
- [ ] Trigger is independent from FastAPI and its cron expression/timezone are documented.
- [ ] Logs include timestamp, job name, status, target date, and run ID where available.
- [ ] Focused, concurrency, migration, pipeline-regression, and broader relevant checks actually pass.
- [ ] Memory bank records the finalized architecture, contracts, validation, and limitations.
- [ ] Required PR evidence is prepared, with no external action taken without authorization.

