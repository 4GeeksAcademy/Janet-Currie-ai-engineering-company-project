# Company Project Context: Backend Serialization Audit

## Purpose

This document is the implementation handoff for the backend serialization-audit branch of the existing AI Engineering company-project monorepo. It defines the required endpoint inventory, serialization classifications, Pydantic input/output contracts, payload minimization, sensitive-field protections, relationship-shaping decisions, verification, documentation, and acceptance criteria.

The implementation agent must audit and correct the existing FastAPI application. Do not create a new repository, generate a replacement backend, or rewrite the API from scratch. Before planning or changing code, inspect the real checkout, active `memory-bank/` files, FastAPI application entry point, registered routers, ORM and TinyDB models, Pydantic version, existing schemas, authentication flows, frontend/API consumers, tests, and established response/error conventions.

This file is context only. No endpoint, schema, model, test, documentation file, or application behavior has been implemented or changed as part of preparing it.

## Authoritative Source

- [4Geeks Academy — Backend Serialization Audit](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-serialization/README.md)

The source was reviewed on September 23, 2026. If this handoff conflicts with newer instructor guidance or a newer authoritative assignment, follow the newer requirement and record the difference before implementation.

## Business Context

The company backend is approaching real-user traffic. Some endpoints may currently return raw ORM objects, broad dictionaries, or schemas that expose more fields than clients need. That creates three kinds of risk:

- **Security:** internal identifiers, password hashes, tokens, audit fields, soft-delete state, or other sensitive/internal attributes can leak into responses.
- **Performance:** large objects and unnecessary nested relationships increase database work, serialization cost, transfer size, and client processing.
- **Contract stability:** clients become coupled to database models and accidental field names, so internal changes can unexpectedly break consumers.

FastAPI's Pydantic schemas are the API serialization layer. They must define what each endpoint receives and returns independently of whatever fields happen to exist on a database object.

## Project Goal

Audit the complete application-owned API surface and make serialization explicit and trustworthy.

The completed branch must:

1. inventory every FastAPI endpoint with method, route, purpose, and current behavior;
2. classify each endpoint's original serialization state;
3. identify actual consumers and the fields each consumer requires;
4. define an intentional target response shape for every endpoint;
5. create or correct Pydantic schemas for incomplete or unsafe contracts;
6. declare an explicit `response_model` on every application route;
7. separate writable request schemas from public response schemas;
8. reduce unnecessary list fields and nested relationships;
9. eliminate sensitive-field exposure, especially in authentication flows;
10. preserve correct frontend and API-client behavior;
11. document original state, decisions, changes, and final status in `docs/serialization-audit.md`;
12. verify the completed contracts with automated tests and manual `/docs` checks.

## Non-Negotiable Minimum

Every application endpoint must have an explicit response serializer/contract before the task is complete. No endpoint may return a raw ORM object under an undefined output contract.

For a normal JSON route, this means an explicit Pydantic `response_model` appropriate to that route. Special routes that intentionally return no body, a file, a stream, or another non-JSON `Response` must still have an explicit, documented FastAPI response contract and must not be treated as an excuse to leave a JSON payload untyped. The implementation agent must reconcile these special cases with the evaluator's expectation that every route decorator declares `response_model`.

Framework-generated routes such as `/openapi.json`, `/docs`, and `/redoc` are not application-owned business endpoints. All registered application routers, mounted application-owned APIs, authentication routes, and health/status endpoints are in scope unless the audit explicitly documents a justified non-Pydantic response type.

## Core Serialization Principles

For every endpoint, answer three separate questions:

1. **What does the endpoint receive?**
2. **What should the endpoint return to this consumer?**
3. **What is it actually returning today?**

The database model is not the public API contract. Schema fields must be intentional.

### Consumers receive only what they need

- Trace the website, backoffice, scripts, tests, and service integrations that call each route.
- Record fields actually read by those consumers.
- Exclude unused model columns and irrelevant related objects.
- Prefer a small list-item schema for collection views when detail fields are not needed.
- Avoid returning entire related records when an ID, label, or flat projection meets the use case.

### Internal changes stay behind the serializer

- Keep public names and types stable unless the audit identifies a security or correctness defect.
- Map ORM/TinyDB attributes into explicit public fields.
- Do not expose a new database column merely because it was added to a model.
- Treat OpenAPI output as a reviewed client contract.

### Sensitive fields are deny-by-default

- Never include plaintext passwords or password hashes in responses.
- Never include reset tokens, access tokens outside their intended token response, internal provider tokens, signing material, or secrets.
- Question internal foreign keys, audit metadata, soft-delete flags, and operational fields unless a documented consumer needs them.
- Do not rely on route handlers remembering to remove secrets manually. The response schema must enforce the safe projection.

## Endpoint Classification

Each endpoint's **original state** must be classified as exactly one of:

### ✅ Already serialized

The route declares an explicit `response_model`, the schema's fields and types match the intended consumer contract, no sensitive or unnecessary fields are exposed, and relationship shaping is appropriate.

### ⚠️ Partially serialized

The route has some response schema or typed output, but one or more of these are true:

- the schema exposes unnecessary or sensitive fields;
- required consumer fields are missing or incorrectly typed;
- list and detail routes share an overly broad shape;
- nested relationships are larger than necessary;
- the decorator lacks the correct explicit `response_model` despite a typed return annotation;
- actual runtime output and documented schema differ;
- input and output schemas are conflated;
- the contract depends on accidental ORM serialization.

### ❌ Not serialized

The route returns a raw ORM/model instance, model collection, arbitrary/untyped dictionary, or other JSON body without a deliberate explicit response schema.

Preserve the original classification in the audit trail. When implementation is complete, add a separate final-status column rather than overwriting evidence of what was found.

## Required Audit Document

Create:

```text
docs/serialization-audit.md
```

The audit document is a required deliverable in its own right. A complete implementation without a complete audit trail does not satisfy the assignment.

### Required summary

Include:

- audit date and branch/context;
- FastAPI application entry point;
- routers and mounted APIs inspected;
- total application endpoints audited;
- counts in each original classification;
- counts corrected;
- final number of compliant endpoints;
- explicit exclusions, such as framework-generated docs routes;
- Pydantic/FastAPI versions and relevant schema conventions;
- tests and manual verification performed.

### Required endpoint matrix

For every application endpoint, record at minimum:

| Field | Required content |
| --- | --- |
| Method and path | Exact HTTP method and registered route. |
| Purpose | Business behavior and intended caller. |
| Authentication | Public, authenticated, role-restricted, or other access rule. |
| Consumer(s) | Website, backoffice view, script, service, docs-only, or other caller. |
| Current response behavior | Raw ORM, dict, typed schema, no body, file/stream, etc. |
| Current `response_model` | Exact model or absent. |
| Actual current fields | Fields observed in the returned payload before correction. |
| Original classification | ✅, ⚠️, or ❌ with rationale. |
| Sensitive/extra-field risk | Passwords, tokens, internal fields, unnecessary nesting, and over-fetching. |
| Target response model | Exact Pydantic schema or explicit special response contract. |
| Target field list | Every field intended to leave the API. |
| Relationship decision | Nested object, related ID, flat projection, or omitted, with rationale. |
| Input schema | Separate request schema for writes, where applicable. |
| Required change | Concrete route/schema/query/client update. |
| Validation | Focused test(s), consumer smoke check, or manual `/docs` case. |
| Final status | Compliant only after implementation and validation. |

The target field list is mandatory for every endpoint changed. Do not write only “needs serializer”; explain why and define the exact intended output.

### Consumer evidence

When a field is kept because a consumer needs it, name the consumer and usage. When a field is removed, record why it is unnecessary or unsafe. Search current frontend and script code rather than assuming what consumers use.

If a public contract must change for security, identify all affected callers and update them in the smallest coordinated change so the application continues to function.

## Authentication Routes: Highest-Priority Review

Begin the audit with authentication because these routes carry the greatest accidental-exposure risk.

Review at least:

- registration;
- login;
- current-user/profile responses;
- forgot-password initiation;
- reset-password completion;
- authenticated password change;
- any token refresh, validation, or logout route that exists.

### Absolute authentication response rules

- No response may contain a plaintext password.
- No response may contain `hashed_password` or any equivalent password hash.
- No response may expose password-reset tokens, internal tokens, signing values, or secrets.
- Unauthenticated register, login, forgot-password, and reset-password flows must not echo the submitted email in the response body.
- `GET /auth/me` may return the authenticated caller's own email because the existing profile view depends on it.
- Login may return the intended access token contract, but must not include unrelated internal token fields or a raw user object.
- Password-recovery responses should preserve existing anti-enumeration behavior and generic confirmations.

Email normally belongs in the request for unauthenticated auth flows. If an existing route currently returns it, treat that as a correction unless a newer authoritative requirement explicitly overrides this rule.

### Recommended auth contract separation

Use distinct schemas according to actual routes, for example:

- credential/registration input;
- safe public user projection;
- authenticated self projection;
- token response;
- generic operation confirmation;
- reset/change-password input.

Names must follow the repository's conventions. Do not create a single broad `UserSchema` that includes every account field and reuse it for all flows.

## Input and Output Schema Separation

For `POST`, `PUT`, and `PATCH` routes, define a request schema that accepts only writable fields and a separate response schema that exposes only safe output fields.

Do not reuse a response schema as a write schema. Doing so can accidentally make server-managed fields writable, including:

- primary keys and UUIDs;
- ownership/user identifiers;
- roles or permissions;
- timestamps;
- computed values;
- password hashes;
- stock balances or other derived fields;
- audit and soft-delete fields.

The schema set may include focused create, update, patch, list, detail, public, self, and result schemas. Avoid unnecessary duplication through carefully chosen shared base models, but do not combine contracts whose allowed fields differ.

### Create schemas

- Include only fields callers are allowed to supply during creation.
- Exclude server-generated identifiers, timestamps, authenticated ownership, and computed values.
- Apply field validation at the request boundary.

### Update/patch schemas

- Include only fields callers are allowed to change.
- Preserve existing full-update versus partial-update semantics.
- Use optionality deliberately; do not make a required domain value nullable merely to reuse a schema.
- Keep privileged fields in dedicated role/admin contracts when the application permits such updates.

### Response schemas

- Include only safe, documented fields.
- Use appropriate types and nullability.
- Enable ORM attribute mapping only when each declared field is intentional.
- Keep response validation active so implementation/schema drift fails visibly during testing.

## List, Detail, and Write-Result Shapes

### List endpoints

List endpoints must return a slim schema designed for the list consumer.

- Include identifiers, labels, status, and summary fields actually needed by the list UI/client.
- Avoid full nested relationships by default.
- Do not serialize large text/blob fields, private metadata, or detail-only fields for every row.
- Preserve pagination/envelope metadata if the existing API uses it.
- Verify query behavior so a new nested schema does not create N+1 database loading.

Do not reuse a detail schema merely because it already exists.

### Detail endpoints

A detail schema may include more safe fields and selected relationships when the detail consumer needs them. “More fields” does not mean “every ORM column.”

### Write endpoints

Return the smallest useful result consistent with existing consumers: a safe created/updated resource, focused result projection, token contract, or generic confirmation. Do not return the input body automatically and do not expose the underlying ORM instance without response filtering.

### Delete endpoints

Preserve the endpoint's established semantics: a documented confirmation schema or an intentional no-content response. Do not fabricate a JSON body for a valid `204` solely to reuse a schema.

## Relationship-Shaping Decisions

For every relationship appearing in a response, deliberately choose one of:

1. **Full nested object** — only when the consumer genuinely needs its safe fields.
2. **Related identifier** — when the client needs to reference the related resource but not display its data.
3. **Flat projection** — when the client needs a few related display fields, such as name/label, without the full object.
4. **Omitted relationship** — when the consumer does not need it.

Document the choice in `docs/serialization-audit.md`.

Avoid cycles and recursive object graphs. Avoid serializing lazy relationships that trigger unexpected database queries. A raw foreign key is not automatically forbidden; it is inappropriate when it is internal-only or when a safer consumer-oriented projection is the actual contract. Conversely, do not expand a single ID into a large nested object if the consumer only needs the ID.

## Pydantic and FastAPI Requirements

- Inspect the installed Pydantic version before choosing configuration syntax.
- For Pydantic v2 ORM-backed responses, use the repository's appropriate `ConfigDict(from_attributes=True)` convention where needed.
- For older versions, preserve the compatible repository convention rather than mixing v1/v2 syntax.
- Declare `response_model=...` explicitly on every application route decorator.
- Use container types accurately for list responses, envelopes, unions, optional bodies, and pagination.
- Do not rely only on Python return annotations when the route lacks the required explicit `response_model`.
- Keep schema modules organized according to the current project structure; do not place every domain schema into one unrelated monolithic file if the repository is modular.
- Reuse schemas only when the complete field set and semantics truly match every consumer.
- Keep OpenAPI output accurate and readable.

If route handlers currently return dictionaries, the explicit response model must still validate/filter them. If they return SQLModel/ORM instances, the response schema must map attributes without exposing undeclared columns.

## Errors and Non-Success Responses

The primary assignment concerns success-response serialization, but serialization changes must preserve the application's established structured error contract.

- Do not return raw exceptions, ORM objects, validation internals, or sensitive data from error paths.
- Preserve intentional HTTP status codes and safe error messages.
- Use FastAPI `responses` documentation or shared error schemas if the repository already has those conventions.
- Do not broaden this branch into an unrelated error-handling rewrite.
- Test error paths whose payload could reveal fields or whose response shape changes with the new schemas.

## Performance Expectations

This is a serialization-performance audit, not only a typing exercise.

For high-volume list and nested endpoints, assess:

- fields removed from the payload;
- unnecessary relationship expansion avoided;
- response byte-size reduction where practical to measure;
- database queries triggered by serialization;
- accidental N+1 loading;
- repeated conversions or transformations;
- compatibility with current pagination.

No universal percentage reduction is required by the source. Record concrete before/after evidence for material optimizations rather than inventing a target. Do not remove fields that active consumers actually use merely to make payloads smaller.

## Required Audit Workflow

### Phase 1 — Inventory and classify

1. Enumerate routes from the running FastAPI application/OpenAPI and cross-check source registrations.
2. Record method, path, purpose, access rule, and consumer.
3. Inspect the route decorator, handler return value, schema, and actual response.
4. List current fields and relationships.
5. Classify the original state as ✅, ⚠️, or ❌.
6. Identify sensitive exposure, unnecessary fields, missing fields, or contract mismatch.
7. Define the exact target output and input contracts.
8. Complete the initial `docs/serialization-audit.md` before implementation.

Source searches alone are insufficient because routers may be included conditionally or paths/prefixes may be applied during registration. OpenAPI alone is also insufficient because it may hide a mismatch between the documented schema and actual handler return. Use both.

### Phase 2 — Implement focused contracts

1. Correct the highest-risk authentication routes first.
2. Create/update Pydantic output schemas for every ⚠️ or ❌ endpoint.
3. Create separate write schemas where input/output are conflated.
4. Add the exact explicit `response_model` to every route.
5. Shape list and relationship payloads to consumer needs.
6. Adjust handler mapping/query logic only where needed to satisfy the intentional contract efficiently.
7. Update affected clients only when a deliberate contract correction requires it.
8. Add focused regression tests alongside each domain change.

### Phase 3 — Verify and close the audit

1. Run focused schema/route tests.
2. Run the complete applicable backend test suite.
3. Run type, lint, and build checks used by the repository.
4. Smoke-test affected frontend/client flows.
5. Manually test at least three representative endpoints through `/docs`.
6. Inspect OpenAPI response schemas.
7. Confirm no sensitive fields appear in success or tested error payloads.
8. Update final status for every endpoint while preserving original findings.

## Testing Requirements

Treat serialization changes as security and public-contract changes. Tests must validate observable payloads, not just status codes.

### Endpoint inventory coverage

Add or use a check that reconciles registered application endpoints with the audit matrix so new/unlisted routes cannot be silently missed. Where practical, verify every JSON route has the required explicit response model, with documented exceptions for intentional non-JSON/no-content responses.

### Response-shape tests

For changed endpoints, assert:

- exact required fields are present;
- sensitive and internal fields are absent;
- types and nullability match the public contract;
- list items use the slim shape;
- detail responses include only the intended expanded fields;
- relationship projection matches the documented decision;
- empty lists, missing optional relationships, and nullable values serialize correctly;
- response validation catches incompatible handler output.

Prefer assertions on meaningful field sets and security exclusions. Avoid snapshots so broad that an accidental new field is accepted without review.

### Request-schema tests

For write routes, verify:

- valid writable fields are accepted;
- read-only/server-managed fields cannot be set by clients;
- extra sensitive fields are rejected or safely ignored according to the project's deliberate schema policy;
- partial update semantics remain correct;
- validation errors remain structured and safe.

### Authentication regression tests

Verify that:

- registration never returns plaintext/hash, tokens beyond the intended contract, or email;
- login returns only the intended authentication result and does not echo email/password/hash or a raw user;
- forgot/reset flows do not echo email, password values, reset tokens, or account-existence details;
- password-change responses contain no credential material;
- `/auth/me` still returns the authenticated user's own email and other safe fields required by the profile consumer;
- invalid authentication/error flows do not leak user records or internal token details.

### Consumer regression tests

Run or update relevant frontend/API-client tests and smoke flows. At minimum, verify authentication, profile, inventory, and other consumers affected by removed/renamed/nested fields. Do not declare an unused field based only on intuition.

## Manual `/docs` Verification

Manually exercise at least three representative endpoints in the FastAPI interactive documentation. Choose cases that demonstrate different risks, preferably:

1. an authentication route with strict sensitive-field exclusions;
2. a list endpoint with a slim item schema;
3. a detail or write endpoint with an intentional relationship or input/output distinction.

For each, record:

- method and path;
- request used, without secrets in committed documentation;
- expected response model;
- observed status and field shape;
- confirmation that sensitive/extra fields were absent;
- any consumer flow verified afterward.

Do not commit real credentials, tokens, password values, personal data, or sensitive screenshots/output.

## Required Initial Analysis

Before changing application code, the implementation agent must identify:

- the actual FastAPI entry point and every included router/prefix;
- all application-owned routes and mounted APIs;
- current `response_model` declarations and return annotations;
- Pydantic and FastAPI versions;
- SQLModel/ORM, TinyDB, dict, dataclass, file, stream, and no-content responses;
- schema-module organization and naming patterns;
- authentication endpoints and credential-bearing models;
- website, backoffice, script, and service consumers for each endpoint;
- list/detail/write/delete patterns;
- relationship loading and potential N+1 behavior;
- server-managed and computed fields that must not become writable;
- existing tests, fixtures, OpenAPI checks, and manual setup;
- existing error-response contracts;
- current uncommitted user changes that must be preserved.

Produce a repository-grounded implementation plan naming the concrete endpoints, source files, schemas, field lists, relationship decisions, consumer changes, tests, and validation commands before implementation.

## Evaluator-Critical Checks

The implementation will be explicitly evaluated for the following:

1. `docs/serialization-audit.md` exists and lists every application endpoint.
2. Every endpoint has an original serialization classification and rationale.
3. Every application endpoint has an explicit route-level `response_model` or a documented intentional special-response contract compatible with evaluator expectations.
4. No JSON endpoint returns an uncontrolled raw ORM object.
5. Input and output schemas are separate where applicable.
6. List endpoints expose only consumer-required fields without unnecessary nested objects.
7. Every relationship shape is intentional and documented.
8. No response exposes password fields, password hashes, internal tokens, or secrets.
9. Unauthenticated register, login, forgot-password, and reset-password flows do not echo email.
10. `GET /auth/me` may continue returning the authenticated caller's email.
11. The audit preserves original state and records changes/final compliance.
12. At least three representative endpoints are manually verified through `/docs`.
13. Existing tests pass and application consumers continue functioning.

## Acceptance Criteria

The serialization branch is complete only when:

- The full application-owned API surface has been enumerated from runtime registration and source.
- Every endpoint appears exactly once per method/path in `docs/serialization-audit.md`.
- Each row records consumer needs, current behavior, original classification, risks, target response model, exact target fields, relationship policy, changes, validation, and final status.
- Every JSON route declares an appropriate explicit `response_model` and no route depends on uncontrolled ORM dumping.
- Intentional no-content/non-JSON routes have explicit, documented contracts and satisfy the evaluator's route-declaration requirement.
- Every ⚠️ and ❌ endpoint has been corrected and revalidated.
- Write endpoints use focused request schemas separate from public responses.
- Server-managed, privileged, computed, credential, and audit-only fields are not writable through broad reused schemas.
- List schemas are lean and do not over-fetch relationships.
- Detail and relationship responses match documented consumer needs without cycles or accidental lazy loading.
- Authentication responses follow every sensitive-field and email rule.
- Current frontend/script consumers continue to work or are minimally updated for an intentional secure contract change.
- Focused response/request/security tests have been added or updated.
- Existing backend tests and applicable type/lint/build checks pass.
- At least three representative endpoints have been verified through `/docs` with safe recorded evidence.
- The final audit marks every endpoint compliant without erasing original findings.
- Existing behavior outside deliberate serialization/security corrections remains unchanged.

## Scope Boundaries

In scope:

- complete FastAPI endpoint inventory;
- `docs/serialization-audit.md`;
- explicit route response models;
- focused Pydantic create/update/list/detail/public/self/result schemas;
- output field filtering and payload reduction;
- input/output separation;
- relationship shaping;
- elimination of sensitive-field exposure;
- minimal query/handler mapping changes needed for efficient serialization;
- minimal consumer updates required by deliberate safe contract changes;
- focused automated tests, OpenAPI inspection, and manual `/docs` verification.

Out of scope unless a newer requirement explicitly adds it:

- rewriting the backend architecture;
- replacing FastAPI, Pydantic, SQLModel, TinyDB, or database technology;
- unrelated authentication, authorization, database, caching, or error-handling redesign;
- arbitrary endpoint renaming or versioning;
- frontend feature work beyond necessary contract compatibility;
- broad performance/load testing unrelated to serialization;
- speculative schema abstractions with no current consumer;
- Git branch creation, commits, pushes, or pull requests without explicit user authorization.

The source suggests branch `feature/serialization-audit` and pull-request title `feat: serialization audit and implementation`. The user has stated that work occurs on a new branch; the implementation agent must inspect the current branch and must not create, rename, commit, push, or open a PR unless explicitly authorized.

## Handoff Expectations

The implementation agent should begin with repository inspection and the complete Phase 1 audit before changing schemas. Keep the active project memory bank current with endpoint counts, classifications, security findings, contract decisions, consumer dependencies, implementation progress, validation results, blockers, and next steps.

Before finalizing:

1. Compare the runtime route inventory against `docs/serialization-audit.md`.
2. Confirm every route has the required explicit response contract.
3. Search schemas and observed payloads for password, hash, token, secret, and forbidden email exposure.
4. Reconcile every list/detail/write relationship decision with real consumers.
5. Verify no write schema accepts unintended read-only fields.
6. Run all focused and applicable full regression checks.
7. Complete and record the three required manual `/docs` checks.
8. Mark final compliance separately from original classification.
9. Report any special-response exception or unverified risk clearly.
10. Update durable implementation memory only after the serialization audit is genuinely finalized.
