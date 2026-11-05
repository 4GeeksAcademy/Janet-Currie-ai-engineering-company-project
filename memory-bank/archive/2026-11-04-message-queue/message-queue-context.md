# HealthCore Message Queue Branch — Implementation Handoff

## Purpose

This document is the execution context for the **message-queue branch** of the existing HealthCore company-project monorepo. This agent must add Redis and Celery so a long-running API operation is queued, processed by an independent worker, observable through a task-status endpoint and Flower, retried with exponential backoff, and moved to a durable Dead Letter Queue after its retry budget is exhausted.


## Authoritative sources

- [4Geeks Academy — Message Queues and Async Tasks](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-message-queue/README.md)
- [Celery — Tasks, retries, states, acknowledgements, and time limits](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Celery — Using Redis as broker and result backend](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
- [Celery — Configuration reference](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [Redis — Key eviction and `noeviction`](https://redis.io/docs/latest/reference/eviction/)
- [Redis — Persistence](https://redis.io/docs/latest/management/persistence/)


## Required starting point


The expected HealthCore codebase already includes some or all of the following completed work:

- a FastAPI backend under the monorepo's `services/` area;
- a Docker Compose development environment;
- authentication and established route/service/error conventions;
- inventory and supplier workflows;
- approved telemetry capture and the `telemetry_events` store;
- a business-performance pipeline and reporting API, including a manual pipeline-run operation;
- a nightly telemetry background process and its `job_runs` state, if the preceding branch has been merged; and
- performance/caching work that may already use Redis or cache abstractions.

This ticket must build on the code that is actually present. It must not recreate, rename, or silently replace those systems. In particular, a Celery task is not a replacement for the independent nightly scheduler, `job_runs`, or `pipeline_runs` unless newer explicit requirements say otherwise.

Before substantial planning or implementation, the implementation agent must:

1. read every applicable repository- and directory-level `AGENTS.md`;
2. read the active root files in `memory-bank/`, then `memory-bank/implementation-memory/index.md`, then only relevant implementation-memory files;
3. inspect the current branch, base branch, recent history, remotes, and working-tree changes;
4. confirm that prerequisite branches/PRs are merged into the intended base before creating or using a feature branch;
5. inspect the actual Compose topology, Dockerfiles, service names, network, ports, mounts, health checks, and environment loading;
6. inspect Python dependency declarations and the supported `uv` workflow;
7. inventory all FastAPI operations and measure or otherwise reproduce their actual runtime with realistic local/test data;
8. identify the slowest existing operation that is appropriate for asynchronous execution;
9. inspect its route, domain service, database transactions, side effects, authorization, inputs, outputs, failure behavior, and tests;
10. inspect existing database models, migrations, sessions, repositories, logging, configuration, and test fixtures;
11. search for existing Redis clients, cache keys, `REDIS_URL`, Celery configuration, task tables, task routes, or Flower configuration so the branch extends rather than duplicates them; and
12. record a repository-grounded plan naming exact files, commands, interfaces, data migrations, tests, and validation scenarios before editing code.

Illustrative paths in this document must be reconciled with the checkout. Preserve unrelated user changes and project conventions. Make the smallest complete change that satisfies Ticket #DEV-55.

## Ticket and business outcome

Implement **Ticket #DEV-55 — Async Task Queue with Redis and Celery**.

Some HealthCore operations take long enough to block the API request-response cycle. The completed branch must change at least one existing heavy operation so that:

1. the API acts as a producer and publishes a lightweight task message;
2. the API immediately returns `202 Accepted` and a task identifier;
3. Redis brokers the message and stores Celery task state/results;
4. an independent Celery worker consumes and executes the operation;
5. a client can poll `GET /tasks/{task_id}` for normalized lifecycle state and a result when available;
6. transient failures retry with exponential backoff rather than immediately;
7. exhausted failures are durably recorded in a Dead Letter Queue with the task ID, attempt, error, and timestamp;
8. task logs provide execution and retry evidence; and
9. Flower provides development-time queue monitoring on port `5555`.

The key architectural boundary is:

```text
Client
  -> FastAPI producer
  -> Redis broker
  -> independent Celery worker/consumer
  -> existing domain operation and data stores

Client
  -> GET /tasks/{task_id}
  -> Redis result backend
  -> normalized task status/result
```

Enqueueing and execution must happen in separate processes. Returning a task ID while continuing the work in the FastAPI process, a FastAPI background task, a thread, an event-loop callback, or an embedded worker does not satisfy the ticket.

## Non-negotiable acceptance criteria

The implementation is incomplete unless all of these are true:

- Redis runs from the official image in Docker, exposes standard port `6379`, and uses the `noeviction` memory policy.
- The API and every Celery worker use the same configured Redis broker.
- Redis configuration is read from `REDIS_URL`; no environment-specific URL is hardcoded in application code.
- Celery uses Redis as both broker and result backend.
- At least one **existing** slow API operation is converted into a Celery task.
- The producer endpoint returns HTTP `202` with exactly the required task identifier payload, at minimum `{"task_id": "..."}`, without awaiting execution.
- With a healthy local broker, the producer response is under `200 ms` regardless of task duration.
- `GET /tasks/{task_id}` returns `task_id`, a lifecycle status, and `result` when available.
- The public status vocabulary is `pending`, `started`, `success`, and `failure`.
- Retries are automatic, capped by the ticket's retry budget, and delayed by exponential backoff.
- Exhausted failures are represented in a durable DLQ record containing `task_id`, attempt number, error message, and timestamp.
- Workers run independently from FastAPI. Stopping the API does not stop a worker or discard already queued messages.
- Task messages contain identifiers/references, not full images, documents, files, reports, telemetry batches, or other large payloads.
- Every task has an explicit maximum execution time.
- A message is acknowledged only after successful task execution, with duplicate-execution risks addressed through idempotent domain behavior.
- Every attempt logs `task_id`, attempt, resulting status, and execution duration; failures also log the complete safe error message.
- Flower runs in development, is reachable on host port `5555`, and shows queued, active, successful, and failed activity needed for the demonstration.
- The monorepo README explains how to start and stop the worker.

## Selecting the operation to convert

The assignment requires the slowest existing API operation, not a fabricated sleep task or a brand-new feature. Do not choose based on intuition alone. Build an endpoint inventory and capture reproducible baseline timing using representative local/test data. Record the operation, dataset, environment, sample count, and representative statistic. Do not profile production or expose production data.

Likely HealthCore candidates to inspect include:

- `POST /reporting/pipeline-runs` if it still executes the business-performance pipeline synchronously;
- report generation or export operations;
- a batch telemetry or inventory operation;
- bulk notifications, if an existing implemented endpoint already provides them; or
- another demonstrably slow operation already present in the checked-out API.

These are candidates, not permission to invent missing behavior. Prefer an operation that is already correct synchronously, has a clear domain-service boundary, and can safely run outside request context. If the manual reporting-pipeline endpoint is selected, the Celery task should invoke the existing pipeline service/flow; it must not copy ETL logic, replace `pipeline_runs`, or alter the independently scheduled nightly process.

The implementation plan must document:

- why the selected operation is the slowest appropriate candidate;
- its measured baseline latency and data scale;
- its existing public request and result contract;
- the identifiers needed by the worker to reload input;
- authorization and ownership rules that must be preserved;
- its side effects and idempotency strategy;
- what result is safe and useful to store in Redis;
- its timeout and expected normal duration; and
- why unselected slow candidates remain synchronous.

Do not convert cheap health, authentication, or ordinary CRUD endpoints merely because they are easy. Do not place request objects, database sessions, open file handles, user tokens, ORM objects, exception objects, or non-serializable values into a task message.

## Required repository deliverables

Exact paths must follow the real monorepo, but the branch must contain the equivalent of:

```text
docker-compose.yml                         # Redis, worker, and Flower services added
services/<celery-module>.py                # Celery application/configuration
services/<task-module>.py                  # selected async task
services/<task-status-route>.py            # GET /tasks/{task_id}
services/<selected-existing-route>.py      # producer now returns 202/task_id
services/<dlq-model-and-service>.py         # durable exhausted-failure record
<database migration for DLQ records>
<focused unit/integration tests>
README.md                                  # worker start/stop and queue operations
<safe environment example/documentation>   # REDIS_URL, never real secrets
```

The assignment suggests `services/celery_app.py`; use that name if it fits the actual package. If imports or existing structure require a different module, preserve the same responsibility and document the verified Celery `-A` target.

Add the required packages through the repository's canonical dependency workflow. The assignment gives:

```bash
uv add celery redis flower
```

Run the command from the actual Python project root and ensure the canonical manifest and lockfile are updated. If this monorepo deliberately maintains `requirements.txt` for its backend image, update it through the established workflow rather than installing packages only into a local environment. Do not hand-edit a lockfile.

## Redis and Docker Compose contract

### Redis service

Extend the existing Compose file; do not replace working application services, networks, volumes, or commands. The Redis service must:

- use an official Redis image pinned according to project convention rather than an unbounded `latest` tag if the repository pins dependencies;
- expose container port `6379`, and publish host port `6379` as the assignment requires unless the checkout has a documented, non-conflicting mapping;
- join the same Compose network used by the API and worker;
- set `maxmemory-policy noeviction` explicitly;
- have a health check such as `redis-cli ping` where Compose readiness is used;
- avoid embedding passwords or other secrets in Compose;
- use a named data volume and Redis persistence when consistent with the development topology; and
- make broker/result loss behavior explicit.

`noeviction` protects queued and result keys from silent eviction, but it means Redis rejects new writes when a configured memory ceiling is reached. If a memory limit is set, size it deliberately and treat broker out-of-memory errors as operational failures. Do not share the queue broker with an application cache using a conflicting eviction policy. If previous caching work already added Redis, inspect whether it uses the same instance/database and either safely isolate broker keys with dedicated logical databases/key prefixes or document a justified separate service. Never run `FLUSHALL` or indiscriminate `FLUSHDB` against a broker containing live task state.

Redis persistence is important if messages should survive a broker restart. For development, a named volume plus AOF (`appendonly yes`, normally `appendfsync everysec`) is a reasonable default when it does not conflict with existing configuration. Worker downtime alone must not lose queued messages. Do not claim zero-loss durability across Redis crashes unless the configured persistence and failure window actually support that claim.

### Service URLs

Inside Compose, `REDIS_URL` must use the Redis service name, for example:

```text
redis://redis:6379/0
```

Do not use `localhost` inside API, worker, or Flower containers to reach Redis; container `localhost` refers to that same container. Host-side commands may need a host-reachable URL such as `redis://localhost:6379/0`. Keep this browser/host/container distinction explicit in environment examples.

### API, worker, and Flower services

- The API publishes tasks but does not start a worker internally.
- The worker must be a separate Compose service/process, preferably reusing the backend image and code so producer and consumer run the same version.
- The worker command must use the verified application target, for example `celery -A services.celery_app worker --loglevel=info`; do not copy that path blindly.
- Flower must be a separate development service/process using the same Celery application and broker, publish `5555:5555`, and be accessible at `http://localhost:5555` during local development.
- Use health/dependency configuration only to express startup readiness that the real services need. `depends_on` ordering alone is not readiness.
- Preserve existing source mounts and Python environment behavior so the worker can import application and domain modules.
- Define graceful worker shutdown and document the supported stop command. Do not use `kill -9` as normal operation.

The evaluator must be able to stop the API while the worker remains alive, and stop/restart a worker while queued messages remain available.

## Celery application contract

Create one Celery instance that both the API and worker import. At minimum, configure:

- broker URL from `REDIS_URL`;
- result backend from `REDIS_URL`, or a deterministic derived Redis URL if the repository deliberately separates broker and result logical databases while retaining `REDIS_URL` as the source configuration;
- explicit task-module discovery/imports;
- JSON task and result serialization unless an existing safe convention requires otherwise;
- accepted content restricted to safe serializers, normally JSON;
- `task_track_started = True` so `STARTED` can be observed;
- timezone-aware UTC operation;
- bounded result retention (`result_expires`) long enough for the expected polling/demo window;
- late acknowledgement for the selected task (`acks_late=True` or the equivalent task-specific setting);
- a soft and hard time limit chosen from measured operation duration;
- broker visibility timeout evaluated against the longest task execution and retry delay; and
- deterministic queue names/routes if a separate application DLQ queue is implemented.

Do not put credentials in source or logs. Fail startup/configuration clearly when `REDIS_URL` is missing or malformed according to the repository's configuration policy. Avoid import-time database connections or execution side effects: importing the Celery app should configure it, not perform work.

### Acknowledgement and duplicate-delivery safety

The assignment requires acknowledgement only after success. Enable late acknowledgement for the selected task. Understand the limits: abrupt worker loss, visibility-timeout redelivery, retry publication, or broker/network ambiguity can cause the same logical task to execute more than once. Therefore the selected operation must be idempotent or explicitly deduplicated at the durable domain boundary.

Examples include a unique operation/run key, an atomic compare-and-set state transition, or an existing idempotent pipeline run/upsert contract. A process-local set or mutex is insufficient. Do not promise exactly-once delivery; implement at-least-once-safe behavior.

Evaluate `task_reject_on_worker_lost` carefully rather than enabling it blindly, because it can create redelivery loops. The visibility timeout must exceed legitimate unacknowledged execution time, but setting it extremely high delays recovery after hard worker loss. Record the chosen values and rationale.

## Async task contract

The selected Celery task must be a thin orchestration boundary around an existing domain operation.

Required behavior:

1. accept only small JSON-serializable identifiers and scalar options;
2. validate those identifiers again inside the worker;
3. open its own repository-idiomatic database/session/unit-of-work context;
4. reload authoritative input from durable storage;
5. call the existing service/pipeline/report operation rather than an HTTP endpoint or duplicated business logic;
6. preserve authorization/ownership decisions established when the task was accepted, using a safe durable reference rather than a bearer token;
7. commit or roll back through established transaction boundaries;
8. return a bounded JSON-serializable result such as a run ID, report ID, count, or status summary—not a large report/blob;
9. close sessions/files/resources on every path;
10. enforce the selected soft and hard time limits; and
11. remain safe if delivered more than once.

If the operation generates a file or large report, store it through the existing durable storage mechanism and return only its identifier/path/reference. If it processes a batch, pass a batch ID or query/run ID; never serialize the complete batch into Redis.

### Retry behavior

Configure automatic retry with:

- `max_retries=3` as explicitly required by the assignment;
- exponential backoff, not immediate re-execution;
- a documented first delay/factor and maximum delay;
- jitter according to the repository's operational/testing needs; and
- a clear list of retryable versus permanent exceptions.

Use Celery's retry machinery so the same `task_id` is retained and the backend records `RETRY`. Do not retry validation errors, missing/unauthorized resources, or other permanent input failures merely to consume the retry budget. Retry transient database, network, storage, or provider failures when safe. Preserve the original exception chain in protected worker logs while exposing only sanitized output.

### Required clarification about attempt counting

The source assignment uses two phrases that are not perfectly aligned with Celery terminology:

- configure `max_retries=3`; and
- move a task to the DLQ after it “fails three times.”

In Celery, `max_retries` counts **retries after the initial execution**, so `max_retries=3` normally permits four total executions. The implementation agent must not hide this distinction. During planning, confirm instructor/project expectations if possible and document one explicit attempt-number convention.

Absent newer clarification, preserve the concrete Celery requirement `max_retries=3`, treat exhaustion after the initial attempt plus three delayed retries as the terminal condition, and record both a human-readable execution attempt and the underlying retry count if useful. Demonstration evidence must make the sequence unambiguous. Do not silently set `max_retries=2` or implement an unlimited retry loop merely to force a different interpretation.

## Dead Letter Queue contract

Redis used through Celery does not provide a RabbitMQ-style broker dead-letter exchange automatically. The branch therefore needs an explicit application-level DLQ design. A failed result in the Celery result backend alone is insufficient because the ticket requires durable database fields and a visible DLQ outcome.

At minimum, create a durable database table/model (use the repository's naming convention, such as `dead_letter_tasks` or `task_failures`) with:

| Field | Required semantics |
| --- | --- |
| `id` | Stable primary key in the project's normal format |
| `task_id` | Celery task ID; unique or idempotently upserted so one exhausted task cannot create duplicate DLQ records |
| `task_name` | Stable registered task name |
| `attempt_number` | Documented execution-attempt or retry number matching the chosen convention |
| `error_message` | Complete useful but sanitized and bounded error message |
| `failed_at` | Timezone-aware UTC timestamp for terminal exhaustion |
| `created_at` | UTC creation timestamp if distinct from `failed_at` |

Optional fields such as a safe input-reference ID, error type, queue name, or correlation/run ID may be added only when they materially improve operations and do not expose sensitive data. Never persist bearer tokens, credentials, full request bodies, large payloads, patient information, raw tracebacks, or arbitrary exception serialization.

Required DLQ behavior:

- retryable failures do not create a terminal DLQ record before the retry budget is exhausted;
- terminal exhaustion writes the DLQ record transactionally and idempotently;
- the record contains the original Celery `task_id` and final attempt/error data;
- concurrent/repeated failure hooks cannot create duplicate records;
- failure to persist the DLQ record is logged as a distinct critical operational failure and is not reported as a successful DLQ move;
- a database migration creates constraints and indexes reproducibly; and
- operators can query the records and correlate them with Flower/worker logs.

If a named Redis/Celery `dead_letter` queue is added for demonstration or later replay, its envelope must also be lightweight and its consumer/replay policy must be explicit. Do not enqueue the original heavy task into a queue that an ordinary worker consumes automatically, because that would create an uncontrolled retry loop. The durable database record is the authoritative ticket evidence unless newer requirements prescribe a specific broker-level DLQ implementation.

Do not build a DLQ replay/admin endpoint unless requested. Manual replay changes data and retry semantics and is outside this ticket.

## Producer endpoint contract

Modify the existing selected endpoint while preserving its authentication, authorization, validation, and route naming unless the approved plan explicitly versions the contract.

The endpoint must:

1. authenticate and authorize the caller before publishing;
2. validate the request and establish any durable input/run record needed by the worker;
3. enqueue through Celery without executing or waiting for the heavy operation;
4. return HTTP `202 Accepted` immediately;
5. return at least `{"task_id": "<celery-id>"}` using a typed response model; and
6. handle broker publication/configuration failure with the project's sanitized structured error contract, normally a retryable `503 Service Unavailable`, without pretending the task was accepted.

Do not call `AsyncResult.get()`, poll, busy-wait, sleep, or run a synchronous fallback inside the request. Do not return `200` for successful enqueueing. Do not include a large input or computed result in the response. If a `Location` header pointing to `/tasks/{task_id}` matches existing API conventions, it may be added without replacing the required JSON.

Measure the under-`200 ms` criterion against a healthy local broker with the heavy operation configured to take materially longer. Report several runs and a representative value; do not claim it from a mocked enqueue-only unit test.

## Task-status endpoint contract

Add:

```text
GET /tasks/{task_id}
```

Use the configured Celery application/result backend to construct an `AsyncResult`; do not reach into Redis keys manually. Return a typed response shaped as:

```json
{
  "task_id": "...",
  "status": "pending | started | success | failure",
  "result": null
}
```

For `SUCCESS`, `result` contains the bounded safe task return value. For non-terminal states, it is normally `null`. For failure, do not serialize the raw Celery exception or traceback to the client; use `null` or an approved safe result/error summary while keeping the required response contract. Protected logs and the DLQ store contain diagnostics.

Normalize Celery's uppercase internal states to the required lowercase public states. The public vocabulary has only four values even though Celery can also report `RECEIVED`, `RETRY`, `REVOKED`, and custom states. Define and test the mapping explicitly. A sensible default is:

| Celery state | Public status |
| --- | --- |
| `PENDING`, `RECEIVED` | `pending` |
| `STARTED`, `RETRY` | `started` |
| `SUCCESS` | `success` |
| `FAILURE`, `REVOKED` | `failure` |

If the project adopts a different mapping, it must still use only the required public values and explain the lifecycle semantics. `task_track_started=True` is required or the `started` phase may never be visible.

Celery treats an unknown/expired task ID as `PENDING`. Decide from existing authentication and task-ownership architecture whether this endpoint may return that state directly or whether an accepted-task registry is needed to distinguish unknown IDs. Do not invent a broad task-registry feature without repository evidence, but do not expose one user's task result to another user. At minimum, preserve the selected endpoint's existing authentication and authorization boundary, validate task ID shape/length, and return only bounded safe result data.

Result expiry must be documented: after Redis result expiration the status may appear `pending` again unless durable application state exists. Choose a retention window long enough for expected client polling and demonstration, and describe it in operator documentation.

## Status lifecycle

The observable happy path is:

```text
request accepted
  -> PENDING / public pending
  -> STARTED / public started
  -> SUCCESS / public success + safe result
```

The retry path is:

```text
PENDING
  -> STARTED
  -> RETRY (public started; delayed by backoff)
  -> STARTED ...
  -> SUCCESS
```

The exhausted path is:

```text
PENDING
  -> STARTED
  -> delayed retries
  -> terminal FAILURE / public failure
  -> one durable DLQ record
```

Do not report success before the selected operation commits successfully. Do not acknowledge a message before successful execution. Do not conflate Celery task state, the existing pipeline's `pipeline_runs`, the nightly process's `job_runs`, or the new DLQ record; these layers may correlate by IDs but retain separate responsibilities.

## Logging and observability

Use the established structured logging setup. Each task attempt must log:

- UTC timestamp;
- registered task name;
- `task_id`;
- attempt number and/or Celery retry count with the convention clearly named;
- resulting/current status;
- execution duration from a monotonic clock; and
- a safe correlation ID such as domain run/report ID when available.

Failures must additionally log the full useful error message. “Full” does not authorize secret or patient-data exposure: sanitize credentials, tokens, connection strings, internal sensitive paths, protected personal data, arbitrary payloads, and unbounded provider/subprocess output. Keep tracebacks in protected worker logs only; never return them through `GET /tasks/{task_id}` or persist them wholesale in the DLQ.

Log meaningful events for publication, task start, retry scheduling/backoff, success, terminal failure, DLQ persistence, timeout, worker shutdown/requeue, and broker connection failure. Avoid duplicate/conflicting terminal logs if both task wrappers and Celery signals are used. Do not log complete task arguments when they may contain sensitive values.

Flower is required development observability, not the durable DLQ database and not production authentication/monitoring. If Flower is exposed beyond local development, secure it according to deployment policy; do not publish an unauthenticated queue dashboard to production as part of this ticket.

## Timeouts, cancellation, and resource limits

Every task must have an explicit maximum execution time based on measurements. Prefer a soft limit that allows cleanup and a larger hard limit that terminates a stuck child process. Test timeout behavior and decide whether it is retryable. Ensure a timeout does not leave a domain row falsely marked successful or a transaction partially committed.

Keep result values bounded and set result expiration. Set worker concurrency and prefetch according to the operation's CPU, memory, database, and external-service behavior rather than maximizing them blindly. A long-running heavy task may benefit from a low prefetch multiplier so one worker process does not reserve many messages. These are repository-dependent decisions and must be recorded if changed.

Do not add user-facing cancellation or revocation endpoints unless the existing operation already requires them. Revocation is not guaranteed rollback of work that has already started.

## Failure handling

Handle and test failures from:

- missing or malformed `REDIS_URL`;
- Redis unavailable during API publication;
- Redis unavailable during worker/result operations;
- Redis write rejection under `noeviction` and a memory ceiling;
- invalid, deleted, unauthorized, or stale input identifiers;
- database connection, transaction, or constraint failures;
- selected-domain-operation failures;
- task serialization/result serialization errors;
- soft and hard timeouts;
- worker graceful shutdown and abrupt loss;
- visibility-timeout redelivery;
- retry publication failure;
- exhausted retry budget;
- DLQ insert/upsert failure; and
- expired or unknown task IDs in the status endpoint.

Catch exceptions at the operation that can handle them. Avoid `except BaseException` and broad swallowing. A retry request is Celery control flow; do not catch it accidentally and mark it terminal. Do not report successful enqueueing if broker publication failed, or successful task completion if the domain operation/DLQ persistence failed.

## Required automated tests

Follow the checkout's testing patterns. Add focused tests for public behavior and durable invariants, not framework internals.

### Configuration and Compose

- `REDIS_URL` is the source of broker/result configuration;
- missing/invalid required configuration fails safely;
- JSON serialization, started tracking, late ack, retry, backoff, result expiry, and time limits have intended values;
- `docker compose config` resolves Redis, worker, and Flower services correctly;
- Redis uses `noeviction`, port `6379`, the intended network, health check, and persistence settings;
- Flower publishes port `5555`; and
- no secret or container-internal `localhost` is hardcoded.

### Producer endpoint

- valid authorized request enqueues exactly one task and returns `202` plus `task_id`;
- the heavy domain operation is not executed in the API process;
- the message contains only expected identifiers/scalars;
- invalid input and unauthorized/forbidden access do not enqueue;
- broker publication failure returns the approved safe error and no false `202`;
- duplicate client submission follows the selected operation's explicit idempotency policy; and
- the response schema and existing authentication/error conventions remain intact.

### Task and retry behavior

- the worker reloads input by ID and calls the existing domain service once per attempt;
- success returns the bounded expected result;
- resources/transactions close or roll back on failure;
- transient failure invokes Celery retry with increasing countdown/backoff;
- retry uses the same `task_id`;
- permanent input errors follow the approved terminal policy;
- time limits are configured and timeout cleanup is correct;
- duplicate/redelivered execution cannot duplicate irreversible business side effects; and
- attempt logs contain task ID, attempt, status, duration, and safe error detail.

### DLQ

- no DLQ row is written before retry exhaustion;
- exhausted failure creates exactly one durable row;
- the row contains correct `task_id`, task name, attempt number, safe full error message, and UTC timestamp;
- repeat/concurrent terminal hooks remain idempotent;
- sensitive task data and traceback text are absent;
- DLQ persistence failure is surfaced and logged; and
- the migration's uniqueness, nullability, indexes, and timestamp behavior work in the actual database.

### Task-status endpoint

- `PENDING`, `STARTED`, `SUCCESS`, and `FAILURE` map to lowercase required states;
- `RETRY`, `RECEIVED`, `REVOKED`, unknown, and expired cases follow the documented mapping;
- success returns the safe result;
- failure never exposes raw exception/traceback/secrets;
- malformed task IDs are rejected safely;
- authentication/ownership boundaries prevent cross-user result disclosure where applicable; and
- backend outage produces the established sanitized API failure behavior.

### Regression

Run the narrow task/API/DLQ tests first, then applicable backend, database migration, reporting/pipeline, nightly-process, authentication, lint, type, and broader test suites. Confirm FastAPI can start without launching a worker and the worker can start without launching FastAPI. If the selected operation is the reporting pipeline, retain its existing pipeline and idempotency tests.

Mock-based unit tests are not sufficient to prove the queue lifecycle. Add or run integration coverage with a real disposable Redis instance and a separate Celery worker in a safe local/test environment.

## Required live validation

Use only local/test services and data. Record exact commands and observed results.

1. Build/start the Compose environment and confirm Redis becomes healthy.
2. Start the independent worker and verify it connects to the intended broker and registers the selected task.
3. Start Flower and open `http://localhost:5555`.
4. Submit the converted endpoint and measure multiple producer responses; confirm HTTP `202`, a task ID, and representative latency below `200 ms` while the operation itself takes longer.
5. Poll `GET /tasks/{task_id}` and observe `pending`, `started`, then `success` with the safe result.
6. Stop the API after enqueueing and confirm the worker continues and completes the task.
7. Stop the worker, enqueue a task, confirm it remains queued, restart the worker, and confirm processing resumes.
8. Force a controlled transient failure and observe increasing retry delays rather than immediate retries.
9. Force terminal exhaustion and confirm public `failure`, one durable DLQ record, safe logs, and Flower evidence.
10. Demonstrate at least one completed task and one failed/DLQ task in Flower as required for submission evidence.
11. Exercise a worker-loss/redelivery or equivalent idempotency scenario and confirm no duplicate business outcome.
12. Restart Redis only if safe and useful, then report the actual persistence behavior rather than assuming it.
13. Stop the environment through documented commands and confirm worker shutdown does not corrupt task/domain state.

Do not claim lifecycle phases passed because they are configured in code. Observe them. If the selected task completes too quickly to observe `STARTED`, use a safe test fixture or controlled test-only delay around the real operation; do not ship an artificial production sleep.

## README and operator documentation

Update the monorepo README with repository-accurate commands and explanations for:

- prerequisites and environment setup;
- `REDIS_URL` for host and Compose contexts;
- installing/synchronizing dependencies;
- starting Redis/API/worker/Flower together and separately;
- the verified worker command;
- the verified Flower command and URL;
- graceful worker shutdown and restart;
- submitting the selected async operation;
- polling `GET /tasks/{task_id}`;
- observing retries and interpreting attempt counts;
- querying the durable DLQ table safely;
- inspecting Flower;
- result-retention/expiry behavior;
- broker persistence and its limitations; and
- common Redis connection, import/discovery, and stale-result troubleshooting.

The README must clearly state that workers are independent from FastAPI and that messages must contain only identifiers/references.

## Submission evidence and Git boundaries

The eventual pull request body must include:

- the selected endpoint/operation and evidence-based justification;
- a screenshot of Flower showing at least one completed task and one failed task associated with the DLQ demonstration;
- a safe log excerpt showing an execution and delayed retry;
- the retry/attempt-count convention;
- validation commands and actual results; and
- any remaining limitations.

The assignment requires a branch pushed to the repository, a PR into `main`, the `async-tasks` label, and merge after approval. Those are submission instructions, not standing authorization. Do not create/switch branches, commit, push, open/label/merge a PR, deploy, touch production services/data, or change credentials unless the user explicitly authorizes the relevant action.

## Scope boundaries

In scope:

- Redis as Celery broker and result backend in Docker;
- one existing heavy API operation converted to an async task;
- one independent worker service/process;
- `GET /tasks/{task_id}`;
- automatic retry with exponential backoff;
- a durable exhausted-failure DLQ record and migration;
- Flower for development monitoring;
- focused logs, tests, README documentation, and local validation; and
- minimal idempotency changes required to make the selected task safe under redelivery.

Out of scope unless a newer requirement explicitly adds it:

- rewriting unrelated endpoints or moving every operation to Celery;
- replacing the independent nightly scheduler with Celery Beat;
- replacing or merging `job_runs` or `pipeline_runs`;
- redesigning telemetry, reports, inventory, authentication, caching, or database architecture;
- putting large reports, uploads, images, documents, telemetry batches, or raw payloads into Redis messages/results;
- building task cancellation, priority, scheduling, chains, chords, replay UI, or DLQ administration;
- production Redis clustering/Sentinel, Kubernetes, autoscaling, or a broad observability platform;
- exposing Flower publicly without security;
- production deployment, infrastructure, or data changes;
- unrelated refactors; and
- unauthorized Git operations.

## Repository-dependent decisions the implementation agent must resolve

Do not guess these before inspecting the checkout:

- correct base branch and whether prerequisite work is merged;
- exact feature-branch name;
- actual FastAPI package/import path and router registration pattern;
- actual slowest eligible operation and measured baseline;
- whether `POST /reporting/pipeline-runs` is synchronous and is the best candidate;
- request/response compatibility strategy for the converted endpoint;
- domain-service boundary and idempotency key/state transition;
- authorization/ownership representation for work executed after the request ends;
- exact Celery module and task module locations;
- backend image, working directory, source mounts, and worker command;
- whether existing Redis/cache infrastructure can be safely reused or must be isolated;
- Redis logical databases/key prefixes, AOF/volume, result expiry, visibility timeout, and memory limit;
- task soft/hard time limits, concurrency, and prefetch;
- retryable exception taxonomy and the assignment's attempt-count ambiguity;
- database engine, ORM, migration tool, table/schema naming, field types, and error-size limits;
- whether accepted-task ownership/registration already exists;
- the public mapping for Celery states outside the required four;
- safe task result schema;
- exact test commands and disposable Redis/worker fixture strategy; and
- environment limitations that prevent full live validation.

These decisions may refine mechanics but may not remove Redis, Celery, the independent worker, `202` response, status endpoint, required four public states, retries/backoff, durable DLQ data, timeouts, lightweight messages, logging, or Flower.

## Completion checklist

Before declaring the implementation complete, the outside agent must verify:

- [ ] Work occurred in the existing monorepo on the correct base.
- [ ] The slowest appropriate existing operation was selected with evidence.
- [ ] Redis uses an official image, port `6379`, and `noeviction`.
- [ ] API, worker, and Flower share the intended broker via `REDIS_URL`.
- [ ] Celery uses Redis as broker and result backend.
- [ ] The producer endpoint returns `202` and `task_id` without executing inline.
- [ ] Healthy-broker response latency is observed below `200 ms`.
- [ ] Worker execution is independent from FastAPI.
- [ ] Messages/results are lightweight and JSON-safe.
- [ ] Late acknowledgement, idempotency, and time limits are implemented.
- [ ] `GET /tasks/{task_id}` exposes the required normalized lifecycle and safe result.
- [ ] Retries use increasing backoff and a documented attempt convention.
- [ ] Terminal exhaustion produces exactly one durable DLQ record with all required fields.
- [ ] Logs include task ID, attempt, status, duration, and safe failure detail.
- [ ] Flower is reachable at port `5555` and shows required demonstration activity.
- [ ] README start/stop/poll/inspect instructions work as written.
- [ ] Focused tests cover success, failure, retries, DLQ, state mapping, timeouts, security, and duplicate delivery.
- [ ] Real Redis/worker integration scenarios were run, not only mocked tests.
- [ ] Applicable regression checks passed or exact pre-existing/environment limitations were reported.
- [ ] No secrets, patient data, raw tracebacks, or large payloads appear in messages, results, logs, fixtures, or DLQ records.
- [ ] Existing nightly, pipeline, telemetry, authentication, and application behavior remains intact.
- [ ] Active `memory-bank/` files contain current status, decisions, validation results, blockers, and next steps.
- [ ] Durable implementation memory is created or updated only after the feature is genuinely finalized.

## Handoff protocol

The outside agent should begin with repository inspection and a concrete, file-specific implementation plan. It must keep the project-local memory bank current throughout implementation in accordance with `AGENTS.md`, add focused tests as part of the change, and run validation proportional to the operational risk of a queue system.

Before handoff, report files changed, the selected operation and rationale, task/result/DLQ contracts, retry and timeout values, Compose topology, tests added, every validation command and result, and any unverified risks. Never claim a queue state, retry delay, worker-isolation property, persistence property, timing target, or test result unless it was actually observed.
