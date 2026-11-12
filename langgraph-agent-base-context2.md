# Project Context: Support Agent with LangGraph — Part 2

## Document purpose

This file is the implementation brief for Cursor for the 4Geeks Academy project **“Support Agent with LangGraph — Part 2 of 2: Tools Outside the RAG.”** It defines the purpose, prerequisites, required behavior, architecture boundaries, failure handling, evaluation criteria, non-goals, and submission evidence.

This is a documentation handoff, not an implementation. Cursor must inspect the actual student monorepo before changing code and reconcile this brief with the repository's instructions, Part 1 implementation, incident service, company briefing, tests, configuration, and dependency versions.

## Source of truth

- Primary assignment source supplied for this analysis: [Support Agent with LangGraph — Part 2](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-langgraph-agent-tools/README.md)
- Required prerequisite: [Support Agent with LangGraph — Part 1](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-langgraph-agent-base/README.md)
- Base repository: [AI Engineering Company Project Monorepo](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo)
- Analysis date: 2026-11-07

If instructor guidance, the actual API contracts in the student's monorepo, or the assigned `company-BRIEFING.md` conflicts with this file, those sources take precedence. Cursor must identify and explain any material conflict before implementing a different interpretation.

## Executive summary

Part 1 converted the existing company RAG flow into a compiled, checkpointed, traceable, and evaluated LangGraph graph. That agent can answer questions from relatively stable company knowledge such as policies, procedures, catalogs, and other indexed documents.

Part 2 adds access to **live operational data**. The required capability is a read-only support-ticket lookup tool that queries the incident manager already built earlier in the company monorepo. The agent must automatically decide whether a user's question needs:

- the existing RAG knowledge base;
- the incident lookup tool;
- both sources; or
- an honest fallback when the required source cannot provide an answer.

The user must not have to name the source or tell the agent to “use a tool.” The graph owns routing. Tool failures, timeouts, and missing tickets must follow explicit recovery paths and must never result in invented ticket data.

An inventory lookup tool is an optional stretch goal and is permitted only if a real inventory manager already exists in the student's monorepo. It must follow the same typed, read-only, timeout, fallback, and tracing rules as the ticket tool.

## Core problem and rationale

The RAG system answers questions about stable knowledge, but incident status is mutable operational data. A ticket can change from open to investigating to resolved at any time. Indexing ticket records into the vector store would create stale copies and blur the boundary between two distinct data sources:

| Source | Intended data | Access pattern |
| --- | --- | --- |
| RAG knowledge base | Relatively stable policies, procedures, catalogs, and company documents | Semantic retrieval from the existing vector store |
| Incident manager | Current ticket/incident status and operational fields | Direct read from the existing live service or its in-process service/repository layer |
| Inventory manager (optional) | Current product and stock data | Direct read from the existing live service or its in-process service/repository layer |

The project is therefore not “another RAG.” It is an extension of the Part 1 graph with narrowly scoped live-data tools and observable routing.

## Required starting state

Part 2 depends directly on a working Part 1 implementation. Before writing Part 2 code, Cursor must verify that the repository already has:

- A typed, minimal LangGraph state.
- Single-responsibility RAG nodes.
- Conditional graph routing.
- A graph compiled before execution.
- Checkpointing at meaningful state transitions.
- A queryable trace for every run.
- At least three Part 1 evals in `tests/pipelines/`.
- A grounded RAG path that still uses the existing company knowledge base.
- A thin FastAPI endpoint, commonly `POST /agent/query`, that invokes the compiled graph.
- Safe error handling without raw stack traces in client responses.

Cursor must also verify that the existing incident manager is real and available through one of the following accepted integration boundaries:

1. HTTP, using `GET /api/incidents` and/or `GET /api/incidents/{id}`; or
2. An existing in-process service/repository interface if the incident manager lives in the same monorepo/package and that is the established architecture.

If Part 1 is absent or materially incomplete, or if the incident manager cannot be found, Cursor must stop and report the exact prerequisite gap. It must not silently rebuild Part 1, invent an incident dataset, or substitute a mock implementation in production code.

## Primary objective

Extend the existing Part 1 graph so that it can answer live incident questions without sacrificing RAG behavior, traceability, testability, safety, or graceful failure handling.

The required outcome is:

1. A typed, read-only ticket lookup tool backed by the real incident manager.
2. A dedicated graph node for incident lookup.
3. Automatic routing between RAG, incident lookup, or both based on the user's question.
4. A concrete numeric timeout on external service calls.
5. Explicit fallback paths for timeout, service error, authentication failure, malformed response, and missing ticket.
6. Traces that show which sources ran and in what order.
7. At least two new evals proving tool-versus-RAG routing.
8. Preservation of all relevant Part 1 and existing RAG behavior.

## Scope

### Required: support-ticket lookup tool

The required tool looks up current incident/ticket information from the existing incident manager.

It must:

- Have a typed input contract.
- Have a typed output contract derived from the actual incident API/service schema.
- Read only from the real incident manager.
- Use either HTTP or the existing in-process service/repository layer.
- Use `GET` operations only when integrated over HTTP.
- Follow existing backend-to-backend authentication conventions when authentication is required.
- Read secrets or credentials from environment/configuration, never hardcode them.
- Define a concrete numeric timeout, commonly in the 3–5 second range unless repository conventions justify another value.
- Return a structured success, not-found, or failure outcome that the graph can route on.
- Never invent a status or operational field when data cannot be confirmed.

### Optional stretch goal: inventory lookup tool

Inventory lookup is optional. Implement it only when a real inventory manager already exists and the required ticket path, routing, tests, tracing, and fallback behavior are complete.

The optional tool must:

- Query the existing inventory service, commonly through `GET /inventory/products` or the actual repository equivalent.
- Use a typed product/stock input and output contract.
- Remain read-only.
- Use a concrete numeric timeout.
- Follow existing authentication/configuration patterns.
- Produce an honest fallback when the service is unavailable or no matching product exists.
- Be implemented as a separate single-purpose tool and graph node.

Do not create an inventory dataset or inventory service merely to satisfy the stretch goal.

## Incident tool contract

The exact types must come from the existing incident API models, OpenAPI schema, Pydantic models, or service interface. Cursor must not guess field names. Conceptually, the contract should resemble the following responsibilities.

### Input

The tool should accept the narrowest typed query supported by the real service, for example:

- `ticket_id`/`incident_id`; or
- existing supported search filters if the user's question is not ID-based.

Input validation should reject missing, malformed, or unsupported identifiers before making the service call.

### Output

The successful result should expose only fields needed to answer support questions, selected from fields the actual incident service already returns, such as:

- canonical incident/ticket ID;
- status;
- category/type;
- source;
- created/updated/resolved dates;
- safe summary or title;
- other company-specific fields required by the existing API contract.

The tool should also expose a machine-readable outcome for graph routing, such as success, not found, timeout, unauthorized, unavailable, or invalid response. The concrete representation must follow repository conventions.

Do not:

- Add fields the source service does not provide.
- Return credentials or sensitive internal error details.
- Treat an error payload as a valid ticket.
- Convert an unconfirmed value into a confident natural-language claim.

## Integration choice: HTTP versus in-process

Both approaches are accepted by the assignment. Cursor must choose the option that matches the repository's existing architecture.

### HTTP integration

Use HTTP when the incident manager is a separate service or when service boundaries are intentionally enforced.

Requirements:

- Use the existing backend HTTP client or dependency already present in the project.
- Configure base URL and credentials through existing settings/environment mechanisms.
- Use only read endpoints.
- Set an explicit numeric timeout on each request.
- Validate response status and body against a typed model.
- Distinguish not-found, authentication, timeout, transport, server, and validation failures.
- Do not add a new HTTP dependency if an appropriate client already exists.

### In-process integration

Use the in-process service/repository layer when the agent and incident manager are part of the same deployable package and direct service reuse is an established convention.

Requirements:

- Call the existing application/service/repository interface, not the database directly from the graph node.
- Preserve authorization and data-access rules that the service normally enforces.
- Keep the tool read-only.
- Define bounded execution behavior; the timeout requirement still applies if the call can block on a database or remote dependency.
- Do not duplicate incident query logic in the agent package.

### Selection rule

Prefer architectural consistency over convenience. What is prohibited is not a particular transport; it is a parallel fake dataset or duplicated incident implementation.

## Graph and state extension

Extend the Part 1 graph rather than replacing it. Preserve the existing RAG nodes, graph compilation, checkpointing, tracing, endpoint integration, and grounding behavior.

The Part 2 state should add only the minimum fields required for routing and tool results. Conceptually, additions may include:

| Field | Purpose |
| --- | --- |
| `route` or `required_sources` | Machine-readable decision: RAG, incident, inventory, both, fallback |
| `incident_query` | Validated incident ID or supported search parameters |
| `incident_result` | Typed result returned by the real incident tool |
| `tool_error` or outcome | Structured routing signal for timeout, not-found, or service failure |
| `sources_used` | Trace/answer metadata showing which source paths completed, if not derived elsewhere |

Do not add full conversation history unless the existing graph already justifies it. Do not store raw HTTP client responses, credentials, or stack traces in graph state.

## Required graph responsibilities

The extended graph should contain clear single-responsibility boundaries for:

- **Request intake/validation:** Existing Part 1 responsibility.
- **Routing:** Decide which source or sources the question requires.
- **RAG retrieval/generation:** Existing Part 1 behavior, preserved.
- **Incident lookup:** Call the typed read-only ticket tool.
- **Tool-result formatting or synthesis:** Convert confirmed tool output into a user-facing answer, or combine it with RAG context when both are required.
- **Fallback/recovery:** Produce an honest response for timeout, unavailable service, missing ticket, invalid tool request, or other handled failures.
- **Terminal response:** Return the answer without exposing internal errors or private model reasoning.

The route decision, tool invocation, result, and recovery path must be visible in the trace.

## Automatic routing behavior

The user must not have to specify the source. The router must infer the required path from the content of the question.

Expected outcomes include:

| Example intent | Expected route |
| --- | --- |
| “What is our escalation policy?” | RAG only |
| “What is the status of ticket 482?” | Incident tool only |
| “What does the escalation policy say, and does ticket 482 meet it?” | Both RAG and incident tool |
| “Do we have stock of product X?” | Inventory tool only, but only if the optional real inventory integration exists |
| Empty or unsupported question | Existing validation/fallback route |

The assignment does not mandate one routing implementation. Cursor may use a deterministic classifier, typed LLM routing output, or an existing repository pattern, provided that:

- the decision is machine-readable and testable;
- routing is automatic;
- the router cannot call arbitrary tools;
- invalid or ambiguous output follows a safe fallback;
- the chosen source path is observable in the trace;
- no hidden chain-of-thought is stored or returned;
- the required evals pass reliably.

If a question requires both sources, the graph must make the order or parallelism explicit and synthesize only from confirmed results. A partial failure must not cause the successful source to be misrepresented; the response should state which requested information could and could not be confirmed.

## Failure and fallback requirements

Tool failure is an expected graph outcome, not an unhandled exception that breaks the run.

At minimum, handle:

- **Ticket not found:** State that the ticket could not be found or confirmed; never invent a status.
- **Timeout:** Stop waiting at the configured numeric limit and route to an honest unavailable response.
- **Connection/service failure:** Report that current status could not be confirmed.
- **Authentication/authorization failure:** Do not retry with hardcoded credentials or expose credential details; produce a safe service-unavailable response and record a sanitized failure for operators.
- **Malformed or schema-incompatible response:** Treat it as an invalid tool result and use the fallback path.
- **Invalid identifier/filter:** Avoid the service call when possible and return a clear validation response.
- **Partial failure on a both-sources route:** Use the successful source only for the part it supports and disclose that the other part could not be confirmed.

A suitable user-facing fallback is conceptually: “I couldn't confirm that ticket's status right now.” The exact wording should match the company voice while preserving uncertainty.

Do not silently redirect a ticket-status question to RAG. The knowledge base is not a valid fallback source for current ticket status.

## Read-only and security constraints

The ticket and optional inventory tools are strictly read-only.

- Do not create, update, close, assign, or delete incidents.
- Do not change inventory or stock records.
- Do not expose POST, PUT, PATCH, or DELETE operations as agent tools.
- Use least-privilege service credentials when authentication is required.
- Load credentials and base URLs through the repository's existing configuration system.
- Never hardcode tokens, API keys, passwords, or URLs that vary by environment.
- Never write credentials, authorization headers, or raw sensitive records to traces.
- Validate and constrain user-derived IDs and filters before using them.
- Do not let natural-language input choose arbitrary URLs, paths, HTTP methods, or tool names.
- Follow existing access-control and data-redaction rules in the incident service.

If the incident service has no authentication, document that fact in the pull request so reviewers do not assume credentials were omitted accidentally.

## Endpoint behavior

Part 2 should normally continue using the compiled Part 1 agent endpoint, commonly `POST /agent/query`. The endpoint remains a thin transport layer.

It must:

- Invoke the extended compiled graph.
- Pass the existing run/thread configuration needed for checkpointing and tracing.
- Contain no routing, ticket lookup, RAG, or answer-synthesis business logic.
- Return a safe final response using existing response schemas where possible.
- Preserve the repository's established error-handling behavior.
- Never expose raw stack traces, credentials, raw HTTP responses, or internal tool exceptions.

The Part 2 README does not require a new endpoint. Do not create one unless the actual repository architecture or instructor guidance requires it.

## Tracing requirements

Extend the Part 1 trace rather than introducing a disconnected tracing system. Every run must make it possible to determine:

- the routing decision;
- whether RAG, the incident tool, the optional inventory tool, or multiple sources were used;
- the order in which nodes/sources executed;
- whether the tool returned success, not found, timeout, or another sanitized failure;
- which fallback path ran, if any;
- whether the run completed successfully or partially;
- the final answer or a safe reference needed for evaluation.

Traces must remain queryable after the run and must not be only console output. Preserve the existing run ID/thread ID correlation from Part 1.

Do not trace private chain-of-thought. Trace graph decisions, node execution, typed inputs/outputs as permitted, status, timing, and sanitized errors.

## Evaluation and testing requirements

### Required new evals

Add at least two new evals in `tests/pipelines/`:

1. **Tool-routing eval:** A ticket-status question must use the incident tool and must not use the RAG path as its source of current status.
2. **RAG-routing eval:** A policy/procedure question must use the RAG path and must not call the incident tool.

The trace must be sufficient to verify the selected path and ordering.

### Recommended third eval

Add a fallback eval in which the incident service times out, fails, or returns not found. Verify that:

- the graph follows the explicit fallback route;
- it does not produce a made-up status;
- the trace records a sanitized tool failure outcome;
- the overall run returns a clear, honest answer instead of crashing.

### Additional focused tests

Where consistent with the project's test patterns, cover:

- Typed input validation.
- Mapping of the real incident response into the typed tool output.
- Authentication headers/config without exposing secret values.
- The concrete timeout configuration.
- Differentiation among success, 404/not-found, timeout, unauthorized, server error, and malformed response.
- Read-only behavior and correct `GET` endpoint selection.
- Mixed questions that require both RAG and incident data.
- Partial failure behavior for a both-sources route.
- Optional inventory routing and fallback, if implemented.
- No state, checkpoint, or trace leakage between runs.

### Test isolation

- Use mocks, stubs, or the repository's test client for focused error-path and routing tests.
- Do not use simulated incident data in production code. Test fixtures are acceptable and necessary for deterministic tests.
- Routine tests should not require a live generation provider.
- Existing RAG and Part 1 graph evals must remain passing.
- Derive the exact single-command test invocation from the actual repository and document it.

## Repository placement

Extend the existing Part 1 layout rather than creating a new agent service:

```text
services/
  <agent-service>/              # Existing graph plus new router/tool node(s) and typed tool contract(s)

tests/
  pipelines/                   # Existing evals plus new routing/fallback evals
```

Reuse existing shared models, settings, HTTP clients, incident service interfaces, and test fixtures where available. Keep the change narrowly scoped.

## Dependencies and configuration

- The assignment states that no new dependency should be necessary beyond the HTTP capability already used by the backend.
- Reuse the repository's current HTTP client or in-process service interface.
- Do not add an unrelated agent framework or replace LangGraph.
- Do not upgrade unrelated packages.
- Add configuration only through the existing settings/environment pattern.
- Document required variable names for incident base URL, timeout, and credentials, but never commit secret values.
- Use one explicit timeout value or a typed configuration value with a concrete default; do not leave the client timeout implicit or unlimited.

## Explicit non-goals

The following are outside the scope of Part 2 unless separately required by the actual repository or instructor:

- Rebuilding or replacing the Part 1 LangGraph foundation.
- Rewriting the existing RAG pipeline.
- Indexing incident tickets or inventory records into the RAG vector store.
- Creating a second or simulated incident dataset.
- Creating a new incident manager or inventory manager.
- Allowing the tools to mutate incidents or inventory.
- Building one multi-purpose tool that handles both incidents and inventory.
- Adding inventory integration when no real inventory service exists.
- Adding MCP; that is a later project in the course sequence.
- Adding persistent conversational memory, self-improvement, or security-harness milestones.
- Adding unrelated tools such as web search, CRM updates, email, or ticket creation.
- Redesigning the frontend or building a new user interface.
- Returning hidden chain-of-thought as “reasoning.”
- Large unrelated refactors, dependency upgrades, deployment changes, or infrastructure work.

## Implementation approach for Cursor

Cursor should follow this sequence after receiving the actual repository:

1. Read root and directory-level instructions, repository rules, current memory bank, and the assigned company briefing.
2. Inspect the Part 1 graph, state, node contracts, router/edges, compiler, checkpointing, tracing, endpoint, and eval fixtures.
3. Run the existing RAG and Part 1 focused tests and record the baseline.
4. Locate the real incident manager, its OpenAPI/Pydantic/service models, endpoints, authentication, configuration, and test fixtures.
5. Confirm the incident service can answer the ticket questions required by this assignment.
6. Choose HTTP or in-process integration based on the existing architecture and document the decision.
7. Define typed tool contracts directly from the actual service schema.
8. Design the smallest state extension and routing contract for RAG, incident, both, and fallback.
9. Add focused tests/evals for routing and failure behavior.
10. Implement the read-only tool, concrete timeout, sanitized failure mapping, graph node, and conditional edges.
11. Extend existing tracing so routes, tools, ordering, and fallback outcomes are queryable.
12. Keep the existing endpoint thin and invoke the extended compiled graph.
13. Run the new focused tests, existing Part 1 evals, existing RAG tests, and applicable lint/type/build checks.
14. Capture the required trace and eval evidence for the pull request.

Cursor must not guess endpoint paths, field names, auth schemes, or environment variables. It must derive them from the actual monorepo.

## Acceptance criteria / definition of done

The project is complete only when all required items below are verified:

- [ ] Part 1's compiled, checkpointed, traceable graph is present and still works.
- [ ] The real incident manager and its read contract have been identified.
- [ ] The incident tool has typed input and output contracts based on the real service schema.
- [ ] The incident tool queries the real incident service through HTTP or its existing in-process service/repository layer.
- [ ] No production code uses a fake, hardcoded, or parallel ticket dataset.
- [ ] The incident tool is strictly read-only.
- [ ] Authentication is passed using existing secure configuration when required, or absence of auth is documented.
- [ ] A concrete numeric timeout is enforced.
- [ ] Not-found, timeout, service error, auth error, and invalid response outcomes cannot produce fabricated status data.
- [ ] The graph has a dedicated incident tool node and explicit recovery route.
- [ ] The agent automatically routes policy questions to RAG and current ticket questions to the incident tool.
- [ ] Questions that genuinely need both sources can run both paths and synthesize only confirmed information.
- [ ] Each tool has one responsibility.
- [ ] Every trace shows which source paths ran and in what order.
- [ ] At least two new evals verify tool-only and RAG-only routing.
- [ ] A fallback eval is included or the fallback path is otherwise verifiably tested.
- [ ] Existing RAG and Part 1 tests/evals remain passing.
- [ ] The existing agent endpoint remains thin and does not duplicate routing or tool logic.
- [ ] No raw stack traces, credentials, or sensitive raw service details are returned to clients.
- [ ] Optional inventory integration, if present, uses the real service and meets the same typed/read-only/timeout/fallback rules.
- [ ] Validation commands and actual results are documented.
- [ ] Pull-request evidence includes a ticket-tool trace, a RAG trace, and new eval output.

## Submission expectations

This is a separate Part 2 pull request, reviewed independently from Part 1.

- Start from the completed Part 1 work.
- Recommended branch: `feature/langgraph-external-tools`
- Required pull-request label: `langgraph-external-tools`
- Expected changed areas:

```text
services/
  <agent-service>/              # New node(s) and tool(s) added to the Part 1 graph

tests/
  pipelines/                   # Routing and fallback evals
```

The pull request must include:

- A trace from a run that used the ticket tool.
- A trace from a run that used the RAG path, proving correct routing.
- Output from running the new evals.
- A note describing the incident integration transport, timeout value, and authentication behavior.

After approval, merge the work into `main` before beginning later milestones so subsequent branches do not start from outdated graph code.

## Open questions Cursor must resolve from the repository

The generic assignment cannot determine the following details. Cursor must discover them before implementation:

1. Is Part 1 complete, merged, and passing its existing evals?
2. Where is the compiled graph defined, and how are state, nodes, checkpointing, and tracing organized?
3. Which endpoint invokes the graph, and what are its real request/response schemas?
4. Where is the incident manager implemented?
5. Are `GET /api/incidents` and `GET /api/incidents/{id}` the actual routes, or does this repository use different paths/prefixes?
6. What typed incident fields and ID types does the service expose?
7. Does ticket lookup require an ID only, or are supported search filters needed?
8. Does the incident service require JWT, API key, service identity, or no authentication?
9. Is the agent-to-incident boundary HTTP or in-process according to current architecture?
10. Which HTTP client/service abstraction is already available?
11. What timeout and retry conventions already exist? The tool still needs a concrete bounded timeout.
12. Which incident fields are safe to expose to the requesting user and to traces?
13. How are trace events stored and queried by run ID?
14. What routing mechanism is already present or best aligned with the Part 1 graph?
15. Does a real inventory manager exist, and is there enough time to pursue the optional stretch goal after all required work passes?
16. What commands run focused evals, all relevant tests, linting, type checks, and service startup?

These are discovery tasks, not permission to broaden the scope. Material prerequisite gaps must be reported rather than filled with invented services or data.

