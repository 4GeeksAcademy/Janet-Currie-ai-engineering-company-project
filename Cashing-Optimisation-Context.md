# Implementation Context — Performance Optimization: Caching

## Purpose of This Document

This file is a handoff for the implementation agent responsible for the caching optimization branch of the HealthCore company project. It describes the required outcome, the current application baseline, constraints, investigation process, implementation expectations, validation, and completion criteria.

This document is context only. Do not treat any suggested cache candidate or duration as already approved: profile the application first and make evidence-based decisions.

## Authoritative Sources

- Assignment: <https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-caching/README.md>


## Branch and Repository Safety

- Inspect the current branch and working tree before making changes.
- Preserve all existing features, tests, performance work, and uncommitted user changes.
- The assignment suggests a branch such as `caching-optimisation`; do not create or switch branches, commit, push, or open a pull request unless explicitly authorized.
- Keep changes limited to profiling, caching, the required frontend optimizations, focused tests, and `CACHING_REPORT.md`.
- Never expose secrets, tokens, passwords, uploaded incident data, or personal information in cache keys, values, logs, fixtures, or reports.

## Project Baseline

HealthCore Digital is a monorepo with:

- `uis/website`: public Next.js site, normally on port 3000.
- `uis/web`: authenticated staff Next.js application, normally on port 3001. This is the backoffice; do not assume a directory named `uis/backoffice` exists.
- `services/api`: FastAPI backend, normally on port 8000.
- `packages/shared`: shared workspace code.
- Docker Compose support, project documentation, scripts, and a project memory bank.

The public website does not currently depend on the FastAPI API. The staff application stores its JWT in browser local storage under `healthcore_access_token` and uses a client-side `AuthGuard`. API data can be backed by TinyDB and SQLModel with PostgreSQL or local SQLite, depending on configuration.

### Existing work that must remain intact

- Public website, staff UI, authentication/profile flows, suppliers, incident analysis, inventory API/UI, Docker Compose, error handling, and test coverage are already implemented.
- The public homepage was optimized into server-rendered sections with small client islands. Language selection uses the `hc_lang` cookie.
- `AppointmentModal` is already dynamically imported with `next/dynamic` and `ssr: false`. Do not automatically count pre-existing work as a new assignment deliverable.
- A prior experiment dynamically importing public below-the-fold homepage sections was rejected because it delayed LCP without a meaningful gain. Do not repeat it without new evidence.
- `uis/web/src/lib/useAsyncResource.ts` is used by staff inventory components. Preserve its established request/loading/error behavior.
- API serialization was subsequently audited: JSON routes use explicit response models, private user fields are not exposed, and CSV/204 contracts are intentional. Caching must not bypass those response contracts.
- The latest known API baseline is 104 passing tests, including serialization audit coverage. Reconfirm the checked-out baseline rather than assuming that count is unchanged.

## Assignment Goal

Improve perceived and measured performance by applying caching and load-reduction techniques only where they provide demonstrated value. The work must show deliberate decisions about:

- which frontend code should be loaded later;
- which expensive frontend calculation should be memoized;
- which backend reads should be cached;
- how long cached results may remain stale;
- how cached results are invalidated when data changes; and
- which tempting candidates should deliberately not be cached.

Quality and justification matter more than the number of optimizations.

## Required Deliverables

### Frontend

1. Identify at least two components or routes suitable for lazy loading and document why.
2. Implement the two lazy-loading decisions using the framework-appropriate mechanism, normally `next/dynamic` or `React.lazy`.
3. Identify at least one genuinely non-trivial computation suitable for `useMemo`.
4. Implement that memoization with complete, correct dependencies.
5. Confirm the changes preserve loading, error, accessibility, authentication, and user interaction behavior.

### Backend

1. Inventory every FastAPI endpoint and assess its cost, expected frequency, data-change rate, authorization scope, and cache suitability.
2. Select at least two endpoints that are expensive enough, called often enough, and stable enough to justify caching.
3. Implement TTL-based caching for at least two endpoints.
4. Invalidate affected cache entries after successful data-changing operations.
5. Prevent private, personalized, session-specific, or sensitive responses from being shared across users.

### Documentation

Create `CACHING_REPORT.md` containing the investigation, measurements, decisions, tradeoffs, implementation details, and results described below. Include at least one frontend or backend candidate that was considered and intentionally not optimized, with the reason.

## Relevant Existing API Surface

Verify this list against the application router registrations and include any missing routes in the audit.

### Public or authentication-related

- `GET /health`
- `POST /users`
- `POST /auth/login`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

### Authenticated users and profiles

- `GET /users`
- `GET /users/{id}`
- `PUT /users/{id}`
- `DELETE /users/{id}`
- `GET /profiles/me`
- `PUT /profiles/me`
- `GET /auth/me`
- `POST /auth/change-password`

### Authenticated suppliers

- `POST /suppliers`
- `GET /suppliers` with country, category, and status filters
- `GET /suppliers/{id}`
- `PATCH /suppliers/{id}`
- `PATCH /suppliers/{id}/rate`
- `PATCH /suppliers/{id}/status`

### Authenticated inventory

- `GET /inventory/products`, including computed current stock
- `POST /inventory/products`
- `GET /inventory/products/{id}`
- `POST /inventory/orders/inbound`
- `POST /inventory/orders/outbound`
- `GET /inventory/orders`, including nested supply summaries

### Authenticated incident workflow

- `POST /api/incidents/analyze` for CSV upload
- `GET /api/incidents/results/export` for CSV export

## Required Investigation Before Implementation

### 1. Map the actual data flow

For every route, record:

- method and path;
- handler and service/repository files;
- authentication and authorization requirements;
- input/query parameters;
- data store and tables/collections accessed;
- aggregation, filtering, serialization, file processing, or external-call cost;
- estimated request frequency;
- expected data-change frequency;
- whether the response varies by user, role, tenant, permissions, or session;
- whether the response contains sensitive data; and
- cache decision and rationale.

Do not infer that a list endpoint is expensive merely because it returns many records. Measure it.

### 2. Add trustworthy timing visibility

Use a monotonic high-resolution clock, such as `time.perf_counter()`, to measure request duration. A timing middleware or equivalent instrumentation should capture method, route/path, status, and elapsed milliseconds.

- Keep logging structured and concise.
- Do not log request bodies, authorization headers, raw tokens, or sensitive query values.
- Ensure timing is recorded for failures as well as successful responses.
- Decide whether instrumentation is permanent, development-only, or configuration-controlled, and document that choice.
- Repeated requests around 100–200 ms or higher are useful investigation signals, not automatic caching thresholds.

### 3. Use realistic data

Small development datasets can conceal expensive behavior. Create or extend an idempotent seed mechanism using valid, non-sensitive synthetic data when needed.

Document:

- approximate row counts before and after seeding;
- which entities were expanded;
- the environment/database used;
- how to reproduce the dataset; and
- whether seed data affects existing tests or development credentials.

Do not alter production data or silently replace the canonical development seed.

### 4. Establish reproducible baselines

For backend candidates, measure multiple comparable requests with the same environment and data. Distinguish cold-cache and warm-cache results and report a representative statistic such as median, not a single best run.

For frontend candidates, use React Profiler, browser Network tools, and production builds/bundle information where available. Look for:

- large code paths not needed for initial interaction;
- heavy dialogs, forms, upload/export tools, charts, or operations panels;
- repeated filtering, sorting, grouping, or derived calculations;
- unnecessary recomputation or rerendering; and
- changes to initial transferred JavaScript and interaction behavior.

## Backend Cache Design Requirements

### Candidate selection

Likely investigation candidates include:

- `GET /inventory/products`, because current stock is derived from inventory movements;
- `GET /inventory/orders`, if joining/serializing order and supply data is measurably costly; and
- filtered `GET /suppliers`, if realistic volume and repeated filter combinations justify it.

These are hypotheses, not instructions to cache all three. Select at least two using measurements.

Likely rejection candidates include cheap health checks, write endpoints, authentication/authorization decisions, user/profile responses, and private incident results. If any user-varying endpoint is cached, the key must safely isolate every relevant user/tenant/permission dimension and the report must justify the risk. Shared caching of personalized or sensitive results is forbidden.

### Cache technology

Acceptable approaches include an in-process TTL cache or Redis. Choose the smallest approach that fits the deployed architecture.

- In-process caching is process-local, disappears on restart, and is inconsistent across multiple workers/replicas.
- Redis is shared and better suited to multi-process deployment, but adds infrastructure, configuration, failure handling, and serialization concerns.
- Do not add Redis merely to appear sophisticated. If in-process caching is chosen, state its deployment limitations clearly.
- Do not use plain `functools.lru_cache` for async, request-scoped, or mutable data unless its lifetime and invalidation semantics are demonstrably correct.

### Keys, values, and boundaries

- Keys must be deterministic and include a schema/version prefix, endpoint identity, and normalized parameters that change the response.
- Include user/role/tenant/permission scope whenever response content can vary by that scope.
- Never place access tokens, passwords, email addresses, uploaded content, or raw personal data in keys or logs.
- Preserve the endpoint's Pydantic response model and serialization behavior on both hits and misses.
- Avoid returning a mutable cached object that a later request can accidentally alter.
- Do not cache exceptions, authorization failures, invalid requests, partial transactions, or server errors.
- Define bounded capacity or eviction behavior so an in-process cache cannot grow without limit.
- Use concurrency protection proportionate to the application to avoid duplicate population or cache stampedes.
- Provide a reliable way for tests and application lifecycle events to clear/reset in-process cache state.

### TTL and freshness

Every cached endpoint must have an explicit TTL derived from how often the underlying data changes and how much staleness users can tolerate. The report must state the freshness/performance tradeoff for each endpoint.

Use monotonic time for local expiry calculations. TTL is a safety bound, not a substitute for invalidation. Also document that direct database changes outside the application can bypass application-level invalidation until expiry.

### Invalidation

Build an explicit read/write invalidation matrix before coding. Invalidate only after the underlying write commits successfully.

At minimum, consider:

- product creation invalidating product collections and related product lookups;
- inbound/outbound orders invalidating computed product stock and order history;
- supplier creation/update/rating/status changes invalidating the supplier record and every affected filtered supplier-list key;
- failed or rolled-back writes leaving valid cache entries untouched.

Prefer clear namespaced invalidation helpers over scattered key deletion. Prefix invalidation is acceptable only when it is deterministic and bounded. Verify that all filter combinations and derived views are covered.

## Frontend Optimization Requirements

### Lazy loading

Find two new, evidence-supported candidates in the current branch. Potential areas to inspect include staff operations panels, incident upload/results UI, inventory movement forms/history, and supplier management UI.

- Do not count `AppointmentModal` automatically because it is already lazy-loaded.
- Do not lazy-load SEO-critical or above-the-fold public content without showing that the performance and UX tradeoff is favorable.
- Use `next/dynamic` for Next.js client components unless another mechanism is better justified.
- Provide an accessible, layout-stable loading state where loading is user-visible.
- Preserve error handling, focus behavior, keyboard access, and authorization boundaries.
- Confirm the code is actually split and excluded from the relevant initial path, rather than merely wrapped in a dynamic API.

### `useMemo`

Select at least one measured or convincingly expensive pure calculation, such as substantial filtering, sorting, grouping, or aggregation over a meaningful dataset.

- Do not memoize trivial string concatenation, small property lookups, JSX merely for style, or asynchronous requests.
- Include every value used by the calculation in the dependency list.
- Keep the calculation pure; do not mutate source arrays or objects.
- Verify behavior when inputs are empty, replaced, reordered, or updated in place.
- Avoid stale results caused by unstable or incomplete dependencies.
- Preserve the existing `useAsyncResource` contract rather than duplicating request-state logic.

Do not convert existing public server components back into client components just to introduce `useMemo`.

## Required `CACHING_REPORT.md` Content

The report must be specific enough for a reviewer to reproduce the decisions:

1. Executive summary and scope.
2. Test environment, build mode, database choice, and dataset sizes.
3. Complete endpoint assessment table: cost, frequency, change rate, privacy scope, and decision.
4. Baseline methodology and results.
5. Frontend lazy-loading candidates selected, evidence, loading behavior, and observed bundle/network impact.
6. Memoized computation, profiler or complexity evidence, dependency rationale, and measured or estimated benefit.
7. For each cached endpoint: exact key shape without secrets, cached value, TTL, invalidation triggers, authorization boundary, and cold/warm measurements.
8. At least one explicit freshness-versus-performance tradeoff.
9. At least one considered-but-rejected endpoint or component and the reason.
10. Multi-worker, restart, external-write, and cache-unavailability limitations.
11. Validation commands and actual results, including any pre-existing failures or unverified risks.

Do not claim performance improvement from a single run or from development-mode measurements when production behavior is materially different.

## Testing Expectations

### Backend focused tests

Add deterministic tests for each applicable behavior:

- first request is a miss and populates the cache;
- equivalent request is a hit and avoids the expensive operation;
- differing parameters or authorization scopes do not collide;
- TTL expiry causes recomputation, preferably using a controllable clock rather than sleeping;
- successful writes invalidate all affected entries;
- failed writes do not invalidate or populate incorrect data;
- errors and unauthorized responses are not cached;
- cached and uncached responses have identical status and schema;
- cache state is isolated between tests; and
- concurrent misses behave acceptably if concurrency protection is implemented.

Retain the security/serialization checks that prevent private fields from appearing in responses.

### Frontend focused tests

Test observable behavior rather than framework internals:

- lazy-loaded functionality still opens/renders and completes its workflow;
- loading and failure states remain usable and accessible;
- the memoized derivation stays correct for empty, changed, reordered, and filtered data; and
- existing authentication and staff workflows remain intact.

### Proportional full validation

Inspect package scripts and run the repository's actual equivalents of:

```bash
cd services/api
uv run pytest

cd ../..
npm run typecheck
npm run lint -w uis/website
npm run lint -w uis/web
npm test -w uis/web
npm run build -w uis/website
npm run build -w uis/web
```

Also run focused tests first and a repeatable timing/profile comparison for the selected optimizations. Do not report a command as passing unless it was actually executed.

## Local Development Reference

Verify commands against current READMEs and package scripts:

```bash
npm install
npm run dev:website
npm run dev:web
npm run typecheck

cd services/api
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

The API documentation is normally available at `/docs`. Inventory uses PostgreSQL when `DATABASE_URL` is configured and otherwise may use local SQLite. Users/profiles and suppliers may use separate TinyDB stores. The cache design and test setup must account for the actual configured store.

## Acceptance Criteria

The work is complete only when all of the following are true:

- Every FastAPI endpoint has been assessed for caching suitability.
- Profiling uses realistic data and reproducible methodology.
- At least two frontend components or routes are newly lazy-loaded with documented justification.
- At least one non-trivial computation uses `useMemo` with correct dependencies.
- At least two backend endpoints use explicit TTL caching.
- Cache keys correctly distinguish all inputs and security scopes that affect results.
- Relevant successful writes invalidate cached data; failures do not corrupt cache state.
- No shared cache exposes personalized, session-specific, or sensitive data.
- Cached and uncached responses preserve existing response-model contracts.
- Focused regression tests cover hits, misses, expiry, invalidation, isolation, and frontend behavior.
- `CACHING_REPORT.md` contains evidence, before/after results, freshness tradeoffs, limitations, and at least one rejected candidate.
- Existing Web Vitals, serialization, authentication, inventory, supplier, and incident behavior remains intact.
- Validation results and any remaining risks are recorded accurately.

## Out of Scope

- Rewriting unrelated application architecture or UI.
- Replacing the existing data stores solely for this assignment.
- Adding a CDN, service worker, broad HTTP caching policy, or distributed cache without measured need.
- Caching authentication decisions, passwords, tokens, raw incident uploads, or private data under shared keys.
- Repeating prior homepage dynamic-import experiments without new evidence.
- Deploying, changing production infrastructure/data, or performing unauthorized Git operations.

## Handoff and Project Memory

Before substantial implementation, read the active project memory files and the relevant implementation-memory index. During work, keep the project memory bank current with material scope, decisions, progress, validation, and blockers. When the caching implementation is finalized, record durable architecture, key namespaces, TTLs, invalidation rules, important files, operational limitations, and maintenance guidance in implementation memory according to the repository's memory-bank conventions.

The final handoff should summarize files changed, selected and rejected candidates, measured results, tests added, all validation results, and remaining limitations. It must clearly distinguish measured facts from estimates.
