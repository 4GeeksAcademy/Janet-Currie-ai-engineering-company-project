# Bullet-Proof Applications Context

## Primary Ticket: AUTH-088

Add unit-test coverage for every authentication endpoint in the existing API.

Required outcomes:

- Cover all authentication endpoints.
- Give every endpoint at least one happy-path test, one edge-case test, and one failure-mode test.
- Use `pytest` for FastAPI/Python logic.
- Use Jest for authentication-related TypeScript utility logic when such logic exists.
- Ensure Python tests pass with `uv run pytest`.
- Ensure applicable TypeScript tests pass with `jest --coverage`.
- Reach at least **70% coverage** on the authentication module, verified with `uv run pytest --cov`.
- Commit the test suite alongside the existing application code.
- Create a root-level `TESTING.md` that explains the test plan, suite coverage, execution commands, coverage results, AI-assisted findings, and any existing bug discovered and fixed by the tests.



## Required Initial Analysis and Test Plan

Before writing tests, inspect and map:

- every authentication endpoint and the business behavior it owns;
- authentication services, dependencies, repositories, models, schemas, and utility functions;
- token creation, validation, expiration, and current-user resolution;
- password hashing and verification;
- persistence boundaries and existing test seams;
- existing fixtures, test configuration, factories, mocks, and repository conventions;
- any authentication-related TypeScript helpers;
- side effects and external dependencies that unit tests must isolate.

Create the initial test plan in `TESTING.md` before implementing the test modules. For each endpoint, list:

- the expected happy path;
- relevant boundary and edge cases;
- expected failure modes;
- the business rule each test proves;
- required setup, fixtures, mocks, and isolation strategy;
- expected observable result.

At minimum, assess empty or missing fields, duplicate users, invalid credentials, malformed tokens, expired tokens, unknown users, and any authorization or ownership rules present in the existing implementation. Add only realistic cases supported by the application's actual contracts.

## FastAPI and Pytest Requirements

- Place Python tests in the FastAPI project's root `tests/` directory, following existing repository conventions if they are more specific.
- Organize tests clearly by authentication endpoint or cohesive behavior. Example names such as `test_register.py`, `test_login.py`, and `test_token.py` are illustrative, not mandatory.
- For every authentication endpoint, implement at least:
  - one happy-path test using valid input and asserting the intended result;
  - one edge-case test exercising a realistic boundary such as an empty field or duplicate user;
  - one failure-mode test such as invalid credentials, an expired token, or malformed input.
- Test the endpoint's decision-making and underlying business logic. Do not spend assertions on HTTP serialization, JSON mechanics, FastAPI internals, or behavior already guaranteed by the framework.
- Isolate tests from production data and external services. Use deterministic fixtures and mocks where appropriate.
- Avoid order-dependent tests and shared mutable state.
- Verify meaningful outputs and state changes, including security-relevant negative behavior; do not assert only status codes when a deeper business result is observable.
- Run `uv run pytest` from the appropriate project root and resolve failures caused by this work.
- Run `uv run pytest --cov` and achieve at least 70% coverage on the authentication module.

The exact cases must be derived from the implementation, but likely high-value behavior includes:

- registration creates a valid user and safely handles duplicates or invalid/empty required fields;
- login accepts valid credentials and rejects invalid or empty credentials;
- passwords are hashed and verified correctly without exposing or comparing plaintext values improperly;
- access tokens contain the required claims and expiration;
- valid tokens resolve the intended user;
- expired, malformed, incorrectly signed, or otherwise invalid tokens are rejected;
- protected authentication behavior rejects missing authentication;
- authorization and ownership checks behave correctly where present;
- missing or inactive users are handled according to the application's contract.



## TypeScript and Jest Requirements

This section applies only if the project contains authentication-related TypeScript utility logic.

- Use the repository's existing Jest configuration, or add `jest.config.ts` or `jest.config.js` at the relevant TypeScript project root if configuration is missing.
- Test authentication utilities such as token generation or parsing, validation, password-related helpers, response handlers, or token-storage helpers only when those functions actually exist and contain testable project logic.
- Give each applicable function at least one happy-path test and one failure-mode test.
- Run `jest --coverage` from the correct workspace or package context and ensure the suite passes.
- Do not add Jest tests merely to restate browser, JavaScript, or framework behavior.



## `TESTING.md` Requirements

Create `TESTING.md` at the project root and keep it accurate as implementation progresses. It must document:

- how to run the Python tests;
- how to run TypeScript tests separately, if applicable;
- what each test suite covers;
- the planned happy paths, edge cases, and failure modes for every authentication endpoint;
- why the selected cases are important;
- final measured coverage for the authentication module;
- at least one test case identified with AI assistance or one bug discovered by the test suite;
- any bug fixed as a result of testing, including the affected behavior and regression test;
- optional backoffice or frontend coverage results if the extra tickets are completed.

Do not claim coverage percentages, passing commands, or bug discoveries unless they were actually observed.

## AI-Assisted Workflow

- Use the coding agent to inspect endpoint logic and propose potentially missed edge cases.
- Use AI-generated boilerplate only as a starting point.
- Review, understand, and adapt every generated test to the actual application contract.
- The implementation agent owns the decisions about what behavior deserves testing.
- Record in `TESTING.md` at least one case that AI helped identify, or one real bug the completed suite exposed.
- If a test exposes an existing application bug, fix the smallest relevant defect and add a regression test that would have caught it. Document the bug and validation result in `TESTING.md`.



## Optional Backlog Work

Complete the following only after `AUTH-088` and all required validation are finished. These tickets are optional and must not delay or compromise the primary authentication suite.

### API-042 — Backoffice Endpoint Tests

**Priority:** Low

- Select at least two existing non-authentication backoffice endpoint groups appropriate to the company's domain.
- Apply the same three-tier structure to each group: happy path, edge case, and failure mode.
- Aim for at least **60% coverage** on the selected modules.
- Add the tests to the existing Python `tests/` structure.
- Add the measured coverage results and relevant commands to `TESTING.md`.



### FE-019 — Frontend Utility Tests

**Priority:** Low

- Identify at least three real utility or helper functions in the existing Next.js/TypeScript frontend.
- Prefer meaningful logic such as input validators, date or currency formatters, response parsers, or token-storage helpers.
- Give each selected function at least one happy-path test and one failure-mode test.
- Place tests in an appropriate frontend `__tests__/` directory, consistent with the repository structure.
- Document the separate frontend test command and results in `TESTING.md`.



## Scope Boundaries

- Work only in the existing company monorepo and on the branch designated for this milestone.
- Focus on tests, narrowly required test infrastructure, `TESTING.md`, and defects genuinely revealed by the new tests.
- Do not redesign authentication, replace established architecture, or perform unrelated refactors.
- Preserve public interfaces and successful existing behavior unless a verified bug requires correction.
- Do not test HTTP serialization or framework internals.
- Do not weaken, skip, or delete valid tests to obtain a passing suite.
- Do not manipulate coverage with tests that execute code without asserting meaningful behavior.
- Never use production credentials, production data, or committed secrets in tests.
- Do not perform branch creation, commits, pushes, pull requests, or other Git mutations unless the user explicitly authorizes them.



## Required Validation

Run the narrowest relevant tests while developing, then perform the complete applicable checks before declaring the work finished:

```bash
uv run pytest
uv run pytest --cov
```

If authentication-related TypeScript logic exists:

```bash
jest --coverage
```

Use workspace-specific command wrappers when required by the monorepo, but preserve the assignment's required underlying test runners. Record the exact commands, project locations, coverage measurements, and outcomes in `TESTING.md` and the active memory bank.

If validation cannot run because of missing dependencies, credentials, unavailable services, or environment limits, state the exact limitation and perform the strongest available alternative check. Clearly distinguish verified behavior from unverified behavior.

## Acceptance Criteria

The implementation is complete only when all required criteria are satisfied:

- `TESTING.md` exists and documents the plan, execution commands, suite coverage, rationale, measured results, and AI-assisted contribution.
- Every authentication endpoint has a happy-path, edge-case, and failure-mode test.
- Tests assert application business logic rather than HTTP serialization or framework behavior.
- `uv run pytest` completes without errors and all Python tests pass.
- `uv run pytest --cov` reports at least 70% coverage on the authentication module.
- Authentication-related TypeScript utilities, when present, have meaningful Jest tests and `jest --coverage` passes.
- Token expiration and invalid-token behavior are explicitly tested so the reported regression cannot recur unnoticed.
- Test names are clear, structure is consistent, fixtures are deterministic, and non-obvious assertions have brief explanatory comments where useful.
- Any application bug fixed during this work has a focused regression test and is documented in `TESTING.md`.
- Existing behavior outside the tested and verified fixes remains unchanged.

The target is not 100% coverage. Prefer a well-reasoned, behavior-focused suite at or above the required threshold over mechanically high coverage with weak assertions.

## Agent Handoff Expectations

Before implementation, produce a repository-grounded plan naming the concrete authentication endpoints, source files, test modules, fixtures, mocks, configuration changes, and edge cases involved. During implementation, keep the active `memory-bank/` files current with material plans, decisions, progress, validation findings, and blockers.

Before finalizing:

1. Reconcile every authentication endpoint against the three required test categories.
2. Confirm the acceptance criteria using actual command output.
3. Update `TESTING.md` with final, observed results.
4. Update the project memory bank with durable implementation details and validation evidence.
5. Report tests added or updated, commands run, results, coverage, bugs found, and any remaining unverified risks.

