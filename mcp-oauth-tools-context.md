# Project Context: OAuth-Protected MCP Server for Company Tools

## 1. Document purpose

This document is the implementation handoff for the 4Geeks Academy milestone **“MCP Server: Connecting Your Agent to the Company's Tools.”** It is intended to be placed in the student's existing company monorepo and given to Cursor before any code is changed.

The objective is not to create a generic MCP demonstration. The objective is to refactor capabilities already present in the company project into an independent, reusable, authenticated MCP service, then migrate the existing LangGraph agent so that incident operations go through that MCP service instead of calling the Incidents Manager directly.

This document defines scope, constraints, expected behavior, discovery work, acceptance criteria, and validation. It deliberately does **not** invent company-specific field names or data contracts. Those must be taken from the existing repository.

## 2. Binding project outcome

Build an OAuth-protected Python MCP server inside the existing company monorepo that:

1. Exposes the company’s existing incident-ticket capabilities through MCP.
2. Exposes read-only access to the company’s existing inventory capability through MCP.
3. Enforces authentication and least-privilege authorization with MCP Auth (`mcpauth`), not FastMCP’s built-in authentication helpers.
4. Publishes sufficient MCP discovery metadata for an external client or agent to understand every tool without reading source code or receiving extra human explanation.
5. Produces traceable audit logs for every tool invocation.
6. Replaces the existing LangGraph agent’s direct Incidents Manager integration with an MCP client integration.
7. Preserves the agent’s current routing behavior between RAG and operational tools.
8. Is demonstrated from MCP Playground using a public GitHub Codespaces forwarded URL and a valid OAuth access token.

The project is incomplete if the MCP server exists but the agent still has an active direct path to the Incidents Manager.

## 3. Existing-system assumption

This milestone is an extension of the student’s **existing fork of the company monorepo**, not a greenfield project and not a separate repository.

The target repository is expected to already contain:

- A company-specific context (`CONTEXT.md`) for Brasaland, TrackFlow, Nexova, or another assigned scenario.
- A centralized backend, typically FastAPI, under `services/`.
- A working Incidents Manager API and its domain schemas/lifecycle.
- A working inventory module and its domain schemas.
- A LangGraph agent with routing between retrieval/RAG and tools.
- A tool or graph node that currently calls the Incidents Manager directly.
- Existing configuration, dependency-management, testing, and logging conventions.

If any of these prerequisites are absent, Cursor must stop after repository discovery and report the missing dependency. It must not fabricate a substitute API or silently create a parallel demo system.

## 4. Mandatory pre-implementation discovery

Before proposing file changes, Cursor must inspect the target repository and record the following facts in a short implementation plan. Search first; do not assume names or locations.

### 4.1 Repository rules and dependency layout

- Read root and directory-level `AGENTS.md`, `README.md`, and relevant `memory-bank` files.
- Read the repository’s company `CONTEXT.md`.
- Identify the Python workspace/package boundaries and the correct `pyproject.toml` for the MCP server.
- Confirm how `uv` is configured and where `uv add` must run.
- Identify established lint, type-check, and test commands.
- Identify environment-variable and settings conventions. Reuse them rather than introducing a second configuration system.

### 4.2 Incidents Manager contract

Locate and document:

- Base URL or in-process service boundary used to reach the Incidents Manager.
- Create-ticket endpoint, request schema, response schema, required fields, and validation rules.
- Read/status endpoint and response schema.
- Exact incident identifier type and name.
- Allowed lifecycle status values and transition rules.
- The required lifecycle endpoint: status changes must use `PATCH /api/incidents/{id}/status`.
- Error formats for missing incidents, invalid transitions, duplicates, and upstream failures.
- Authentication or internal-service credentials already required by the backend.
- Existing client/service abstractions that should be reused.

The MCP implementation must use the real company API and exact company domain values. A generic ticket model is not acceptable.

### 4.3 Inventory contract

Locate and document:

- Existing read endpoints or service methods.
- Supported filters, pagination, sorting, identifiers, locations, SKUs, and response schemas.
- Whether inventory data is location-scoped, tenant-scoped, or otherwise restricted.
- Existing authorization checks.
- All existing mutation paths so the MCP layer can be structurally prevented from reaching them.
- Error behavior for missing, invalid, or inaccessible inventory records.

### 4.4 Agent graph and direct-tool path

Locate and document:

- Graph construction and routing logic.
- The node/tool that calls the Incidents Manager directly.
- Tool names or descriptions the model currently sees.
- State schemas, message formats, checkpointing, and dependency injection used by the graph.
- The decision boundary between RAG and tools.
- Tests or evaluation cases that prove the current routing behavior.
- Every call site for the old direct incident tool, including imports, registries, prompts, and test fixtures.

### 4.5 Authentication compatibility

Inspect the exact versions and APIs available for:

- The selected Python MCP SDK/FastMCP implementation.
- The Python MCP Auth package named `mcpauth` by the course brief.
- `langchain-mcp-adapters` and the currently installed LangChain/LangGraph versions.
- The chosen OAuth 2.1/OIDC provider and its metadata, issuer, JWKS, audience/resource, and scope support.

The course brief is the binding contract: the server must use Python and MCP Auth, and must not use FastMCP’s built-in auth layer. Upstream libraries have evolved; current examples may not match the repository’s pinned Python versions. Cursor must resolve compatibility from installed package documentation and lockfiles rather than copying a mismatched example or switching stacks without approval.

## 5. Scope

### 5.1 In scope

- One company-tools MCP server under `mcps/<company-tools-name>/`.
- Standard MCP tool discovery and invocation.
- Incident creation.
- Incident status lookup/current-state retrieval.
- Incident status updates through the dedicated lifecycle endpoint.
- Read-only inventory queries.
- Explicit rejection of inventory mutation attempts.
- OAuth 2.1/OIDC protected-resource metadata.
- Bearer JWT validation using MCP Auth.
- Endpoint- and/or tool-level scope enforcement.
- Structured authentication, authorization, validation, upstream, and internal errors.
- Audit logging for every attempted tool invocation.
- Agent-side MCP client configuration with bearer-token propagation.
- Replacement of the direct incident tool in the LangGraph path.
- Focused automated tests and documented MCP Playground evidence.
- MCP server documentation, configuration documentation, and run/test instructions.

### 5.2 Out of scope

- Creating a new repository.
- Rebuilding or replacing the Incidents Manager.
- Rebuilding or replacing the inventory backend.
- Adding inventory write capabilities.
- Rewriting the agent, its RAG implementation, prompts, UI, or unrelated graph nodes.
- Refactoring unrelated monorepo code.
- Replacing the company’s existing identity provider unless no compliant provider exists and the user explicitly expands scope.
- Production deployment, infrastructure changes, or secret provisioning unless explicitly requested.
- Adding unrelated MCP resources or prompts merely to demonstrate the protocol.
- Keeping a fallback direct Incidents Manager path after migration.

## 6. Recommended architecture

The intended data flow is:

```text
External MCP client or existing LangGraph agent
        |
        | Streamable HTTP + OAuth Bearer token
        v
Company-tools MCP resource server under mcps/
        |
        |-- MCP discovery and validated tool input
        |-- MCP Auth token verification and scope enforcement
        |-- per-invocation audit logging
        |
        +--> Existing Incidents Manager API/service
        |      - create incident
        |      - get incident/status
        |      - PATCH /api/incidents/{id}/status
        |
        +--> Existing inventory read API/service
               - query only
               - no mutation-capable dependency exposed
```

### 6.1 Transport decision

Use **Streamable HTTP** unless repository inspection reveals a binding incompatibility that must be escalated.

Rationale:

- The service must be reusable by multiple remote clients.
- The MCP Playground must connect through a public Codespaces forwarded URL.
- HTTP carries OAuth bearer headers and supports protected-resource discovery.
- `stdio` is appropriate for a local child process but does not satisfy this remote, OAuth-protected, multi-client validation scenario by itself.

Document the final transport choice in both the MCP README and pull-request description.

### 6.2 Service boundary

The MCP server is an adapter/resource-server layer, not a second business backend. Tool handlers should:

1. Receive and validate MCP inputs.
2. Obtain verified identity and scopes from the MCP Auth context.
3. Enforce tool-specific permissions.
4. Call an existing incident or inventory client/service through a narrow interface.
5. Normalize the result into a documented MCP output schema.
6. Emit one audit event with the result classification.

Do not duplicate incident lifecycle rules or inventory business calculations if those rules already live in the backend. Preserve the backend as the source of truth.

## 7. Tool capability requirements

The brief requires capability coverage, not a particular number of tool functions. Prefer separate, narrowly scoped tools because their schemas and permissions are easier for an agent to understand and safer to authorize. Suggested conceptual tools are below; final names and fields must follow project conventions.

### 7.1 Create incident

Purpose: create a ticket in the real Incidents Manager.

Requirements:

- Input schema exactly reflects the existing create request, including required company identifiers and domain values.
- Reject malformed or unknown values before calling the backend where practical.
- Return the created incident identifier, status, and other fields needed by a client to continue the workflow.
- Require a dedicated incident-write/create scope.
- Preserve upstream validation details in a safe, machine-readable error without leaking internals.

### 7.2 Get incident status

Purpose: retrieve an incident’s current state/status from the real Incidents Manager.

Requirements:

- Accept the exact incident identifier used by the company API.
- Return an unambiguous not-found error when appropriate.
- Return the current lifecycle status and any minimally necessary contextual fields.
- Require an incident-read scope.

### 7.3 Update incident status

Purpose: move an incident through the existing lifecycle.

Requirements:

- Call `PATCH /api/incidents/{id}/status`; do not issue a generic patch to the incident resource.
- Accept only lifecycle values and transitions supported by the existing backend.
- Distinguish an invalid input from a forbidden/invalid lifecycle transition.
- Require an incident-write/update scope.
- Return the resulting status and incident identifier.

### 7.4 Query inventory

Purpose: retrieve inventory information without permitting any mutation.

Requirements:

- Reuse the company’s actual inventory fields, filters, and identifiers.
- Require an inventory-read scope.
- Expose no inventory create, update, adjust, delete, reserve, receive, or transfer tool.
- Depend only on a read-only inventory interface/client. A handler must not receive a general backend client with mutation methods when a narrower read client can be used.
- Add an explicit server-side policy guard so an attempted mutation or unsupported action is rejected with a stable error such as `INVENTORY_READ_ONLY`; absence of a published write tool alone is not sufficient for this assignment.
- Test the rejection path intentionally and document the result.

## 8. MCP discovery contract

An external agent with no company-specific briefing must be able to inspect tool discovery and understand how to use the server.

For every tool, publish:

- A stable, action-oriented name.
- A description stating what the tool does.
- A description stating what the tool does **not** do when the boundary matters.
- When the tool should be used.
- Required scope or permission.
- Complete input schema with types, required/optional fields, formats, constraints, and domain-value descriptions.
- Complete output schema with success fields and meanings.
- Expected error categories.
- Read-only semantics for inventory.

Descriptions must be operationally specific. Avoid vague descriptions such as “manage a ticket” or “work with inventory.” Do not rely on prompts or source-code comments to fill gaps in MCP discovery.

## 9. Authentication and authorization

### 9.1 Authentication requirements

- Use MCP Auth (`mcpauth`) as directed by the project brief.
- Do not use FastMCP’s built-in OAuth/auth helpers as a substitute.
- Operate as an OAuth protected resource, not as a homegrown token issuer.
- Publish Protected Resource Metadata required for MCP client discovery.
- Validate bearer JWT signature, issuer, audience/resource, expiration, and required claims against a compliant OAuth 2.1/OIDC provider.
- Reject missing, malformed, expired, incorrectly issued, incorrectly addressed, or otherwise invalid tokens.
- Protect discovery/listing as well as invocation: a client without a valid token must not list or call company tools.
- Never log raw access tokens, authorization headers, client secrets, or private keys.

### 9.2 Least privilege and scopes

Define scopes that separate read and write authority. Exact names should match repository/provider conventions, but the permission model must distinguish at least:

- Incident read/status access.
- Incident creation/status-update access, split further if the provider and existing design support it.
- Inventory read access.

Enforce required scopes at the narrowest supported boundary, ideally per tool. A valid token with the correct audience but missing the tool’s required scope must be rejected.

Inventory mutation is prohibited regardless of token scope. No “admin” or broad token may bypass the MCP server’s read-only inventory policy.

### 9.3 Configuration and secrets

Reuse the repository’s settings pattern and document all required values, likely including:

- MCP public resource/server URL.
- OAuth/OIDC issuer or authorization-server metadata URL.
- Expected audience/resource identifier.
- JWKS discovery derived from provider metadata.
- Supported/required scopes.
- Incident and inventory upstream base URLs if not in-process.
- Agent MCP server URL.
- Agent credential/token source appropriate to the existing environment.
- Timeouts and safe retry settings if configurable.

Provide `.env.example` placeholders where the repository convention calls for them. Never commit working tokens or secrets.

## 10. Errors and result semantics

Authentication, authorization, input validation, business-rule failures, upstream failures, and internal failures must not collapse into a generic error.

Define a stable error taxonomy and document how each maps to HTTP/MCP behavior. At minimum cover:

| Category | Example machine code | Expected meaning |
|---|---|---|
| Authentication | `AUTH_REQUIRED`, `INVALID_TOKEN`, `TOKEN_EXPIRED` | No usable identity was established |
| Authorization | `INSUFFICIENT_SCOPE` | Identity is valid but lacks the required permission |
| Read-only policy | `INVENTORY_READ_ONLY` | A mutation was attempted against the inventory capability |
| Input validation | `VALIDATION_ERROR` | Tool arguments are malformed or violate the declared schema |
| Not found | `INCIDENT_NOT_FOUND`, `INVENTORY_NOT_FOUND` | Requested company entity does not exist or is not visible |
| Lifecycle conflict | `INVALID_STATUS_TRANSITION` | Requested incident status change violates the existing lifecycle |
| Upstream dependency | `UPSTREAM_UNAVAILABLE`, `UPSTREAM_TIMEOUT` | Existing backend could not complete the operation |
| Internal | `INTERNAL_ERROR` | Unexpected server failure with no sensitive detail exposed |

At the HTTP authorization boundary, unauthenticated requests should produce the standards-compliant authentication response expected by MCP Auth, including the appropriate discovery challenge. For authenticated MCP tool calls, return structured tool errors that a model/client can understand and potentially recover from. Preserve a correlation/request ID across logs and error responses.

Do not expose stack traces, tokens, database details, or internal URLs in client-facing errors.

## 11. Audit logging and observability

Emit at least one structured audit record for every tool invocation attempt, including failures.

Each record should contain, where available:

- Timestamp in a consistent format.
- Correlation/request ID.
- Authenticated subject or stable client identifier.
- Tool name.
- Outcome: success, denied, validation failure, upstream failure, or internal failure.
- Stable result/error code.
- Duration.
- Safe target identifiers needed for traceability.

Do not log:

- Bearer tokens or authorization headers.
- Client secrets or signing material.
- Entire request/response bodies by default.
- Sensitive ticket descriptions, personal data, or confidential inventory content unless the existing data policy explicitly allows it.

Use the repository’s logging system and format. Logging is not an excuse to add a second observability stack.

## 12. LangGraph agent migration

### 12.1 Required change

Use `langchain-mcp-adapters` as required by the course brief to load the MCP server’s tools into the existing LangGraph agent. For HTTP transport, propagate the OAuth bearer token through the supported header/configuration mechanism.

Replace the graph node/tool binding that calls the Incidents Manager directly. Preserve graph state and routing contracts unless a minimal compatibility change is necessary.

### 12.2 Single-path requirement

After migration:

- The agent has exactly one active path to incident operations: the MCP server.
- The old direct incident tool is removed or clearly deprecated and is not registered, imported, selected, or reachable at runtime.
- Prompts and tool descriptions no longer direct the model toward the old implementation.
- Tests and fixtures use the MCP path.

Repository-wide search must confirm that no active agent execution path calls the Incidents Manager directly.

### 12.3 Routing preservation

The migration must not change the intent boundary between retrieval and operational actions.

At minimum verify:

- Knowledge/document questions still route to RAG.
- Incident create/status/update requests route to MCP tools.
- Unsupported requests retain existing fallback behavior.
- MCP failures do not silently divert to the deprecated direct tool.
- Existing conversation/checkpoint behavior remains intact.

## 13. Suggested repository placement

Follow the actual repository conventions, but the expected shape is conceptually:

```text
mcps/
└── <company>-company-tools/
    ├── README.md
    ├── pyproject.toml or workspace-integrated package metadata
    ├── src/
    │   └── <package>/
    │       ├── server.py
    │       ├── auth.py
    │       ├── config.py
    │       ├── errors.py
    │       ├── logging.py
    │       ├── clients/
    │       │   ├── incidents.py
    │       │   └── inventory_readonly.py
    │       └── tools/
    │           ├── incidents.py
    │           └── inventory.py
    └── tests/
```

This is a responsibility map, not a mandate to create every file. Prefer the smallest structure consistent with the monorepo. Do not put the MCP server under `services/`; the course explicitly requires `mcps/`.

## 14. Dependency-management constraints

- Add Python dependencies with `uv add` in the correct workspace/package context.
- Do not use `pip install` directly.
- Commit the appropriate `pyproject.toml` and lockfile changes when implementation is performed.
- Add only dependencies required for the server, MCP Auth integration, client adapter, configuration, and tests.
- Confirm compatible versions before coding.

The brief names `fastmcp`, `mcpauth`, and `langchain-mcp-adapters` as expected dependencies/examples. Do not assume their latest releases are mutually compatible with the existing lockfile.

## 15. Testing requirements

Implementation and validation are one scope. Add focused automated tests using the repository’s existing test style.

### 15.1 Tool and schema tests

- Discovery lists the expected tools for an authorized client.
- Tool names, descriptions, and schemas contain the required information.
- Valid incident-create input maps correctly to the existing API.
- Incident status lookup returns the company’s real schema/domain values.
- Status update calls the dedicated `/status` lifecycle endpoint.
- Inventory filters and output map correctly to the existing read API.
- Malformed and boundary inputs return stable validation errors.

### 15.2 Authentication tests

- Missing token cannot initialize/list/invoke tools.
- Malformed token is rejected.
- Expired token is rejected.
- Wrong issuer is rejected.
- Wrong audience/resource is rejected.
- Valid token with correct claims is accepted.

Use cryptographically meaningful test fixtures or the provider’s recommended test approach. Do not disable signature verification in tests that claim to validate authentication.

### 15.3 Authorization tests

- Incident-read scope cannot perform incident writes.
- Inventory-read scope can query inventory.
- A valid token without the required scope is denied.
- Inventory mutation is rejected even for a broadly privileged identity.
- Scope denials are distinct from authentication failures.

### 15.4 Error and audit tests

- Not-found, invalid transition, validation, timeout/upstream, and internal failures map to distinct codes.
- Client-facing errors do not leak secrets or stack traces.
- Every success and failure creates an audit log record.
- Logs include client/subject, tool, outcome, and correlation ID.
- Logs do not include raw bearer tokens.

### 15.5 Agent regression tests

- Existing RAG routing cases still pass.
- Incident intents invoke MCP-loaded tools.
- The agent passes an authorization header to the MCP client path.
- An MCP error is surfaced through existing agent behavior without calling the old direct tool.
- No direct incident tool remains registered.

### 15.6 Integration tests

- Run the MCP server against controlled/stubbed existing APIs for deterministic tests.
- Run at least one end-to-end authorized incident flow against the intended development environment.
- Run an authorized inventory query.
- Run an unauthorized request and an insufficient-scope request.
- Run an intentional inventory write attempt and capture the controlled rejection.

## 16. MCP Playground validation

Manual Playground validation is mandatory and supplements, not replaces, automated tests.

1. Start the MCP server in GitHub Codespaces.
2. Forward its HTTP port.
3. Change the forwarded port visibility as needed so MCP Playground can reach it.
4. Use the full public Codespaces forwarded URL, including the correct MCP path. `localhost` will not work from the hosted Playground.
5. Authenticate with a valid access token using the supported Playground flow/configuration.
6. Confirm discovery shows accurate tool descriptions and schemas.
7. Execute one complete successful flow for every exposed tool/capability.
8. Verify incident status changes use the lifecycle endpoint.
9. Attempt an inventory mutation and confirm a controlled, explainable read-only rejection.
10. Test missing/invalid authentication and insufficient scope.
11. Capture non-secret evidence: request purpose, tool selected, sanitized inputs, result/error code, timestamp, and relevant log correlation ID.

Do not place access tokens in screenshots, committed logs, README examples, or pull-request text.

## 17. Documentation deliverables

The implementation should leave enough documentation for another engineer to run and evaluate it without oral guidance.

The MCP server README should include:

- Purpose and architecture.
- Prerequisites.
- Dependency/setup command using `uv`.
- Environment variables with safe placeholders.
- OAuth provider assumptions and resource/audience/scopes.
- Transport choice and rationale.
- Local/Codespaces run command.
- MCP endpoint and protected-resource discovery behavior.
- Tool catalog and read-only inventory guarantee.
- Error-code table.
- Test commands.
- MCP Playground procedure.
- Agent integration/configuration.
- Known limitations.

Update broader monorepo documentation only where necessary to register the new MCP server and the agent’s new dependency.

## 18. Implementation sequence for Cursor

Cursor should follow this order after the user authorizes implementation:

1. Perform and report the mandatory repository discovery.
2. Produce a concise plan tied to actual files and existing contracts.
3. Resolve dependency/API compatibility without changing the mandated stack.
4. Define tool schemas, scopes, errors, and read-only boundaries from actual domain models.
5. Build the narrow upstream clients/adapters.
6. Wire MCP Auth protected-resource metadata and bearer validation.
7. Register discoverable, scope-protected tools.
8. Add structured audit logging.
9. Add focused server tests and run them.
10. Migrate the LangGraph incident path to MCP.
11. Remove/deactivate the old direct path.
12. Run routing regression tests and repository-wide searches.
13. Run authorized/unauthorized integration checks.
14. Validate through MCP Playground using the Codespaces forwarded URL.
15. Complete documentation and evidence.

Do not begin with broad refactoring. Make the smallest changes that satisfy the contract.

## 19. Definition of done

The work is done only when all statements below are true:

- The server exists under `mcps/` and starts with documented commands.
- It uses Python and a standard MCP SDK such as FastMCP.
- MCP Auth protects the server; FastMCP built-in auth is not used as a substitute.
- Unauthenticated clients cannot list or invoke tools.
- Tokens are validated for signature, issuer, audience/resource, expiration, and required scopes.
- Incident creation uses the real company Incidents Manager.
- Incident status retrieval uses the real company Incidents Manager.
- Incident status updates use `PATCH /api/incidents/{id}/status`.
- Inventory queries use the real company inventory implementation.
- Inventory writes are impossible through exposed tools and are explicitly rejected when attempted.
- Tool discovery is complete enough for an unfamiliar external agent.
- Authentication, authorization, validation, lifecycle, upstream, and internal errors are distinguishable.
- Every tool invocation is auditable by client/subject, tool, and result without secret leakage.
- The LangGraph agent loads and calls MCP tools with `langchain-mcp-adapters` as required by the brief.
- The agent has no active direct Incidents Manager path.
- RAG-versus-tool routing behavior is preserved.
- Focused automated tests pass.
- MCP Playground validation succeeds through the public Codespaces forwarded URL.
- Documentation and sanitized evidence are complete.
- The implementation is delivered through the monorepo’s normal branch/PR flow when the user requests Git operations.

## 20. Explicit prohibitions for the implementation agent

Cursor must not:

- Start a new repository or standalone demo.
- Invent generic incident or inventory fields instead of reading the existing APIs.
- Use a generic incident patch endpoint for lifecycle transitions.
- Expose any inventory mutation tool.
- Treat absence of a write tool as the only read-only safeguard.
- Leave tools/list or tool execution unauthenticated.
- Treat a valid token as automatically authorized for every tool.
- Replace MCP Auth with FastMCP auth helpers.
- Install dependencies with `pip install`.
- Keep the old direct incident tool as an active fallback.
- Break or redesign RAG routing to make the migration easier.
- Log tokens, secrets, sensitive payloads, or unredacted credentials.
- Claim Playground or test validation without actually running it.
- Commit, push, merge, or deploy unless the user explicitly authorizes those Git/deployment actions.

## 21. Open facts Cursor must resolve from the target repository

These are not product ambiguities to guess; they are repository facts to discover:

- Assigned company and MCP package name.
- Exact incident and inventory field names/types.
- Exact incident lifecycle statuses and transition rules.
- Exact read filters and result shapes for inventory.
- Existing API authentication between services.
- Existing OAuth/OIDC provider and token-acquisition method.
- Final scope names.
- MCP server port/path and configuration mechanism.
- Exact `uv` workspace/package command.
- Exact agent graph node/tool to replace.
- Exact test, lint, type-check, and run commands.
- Exact versions/API surface of `mcpauth`, the MCP SDK, and LangChain integration packages.

If a fact cannot be discovered safely, Cursor should ask one focused question rather than invent it.

## 22. Source references

- Primary assignment: [4Geeks Academy — MCP Server: Connecting Your Agent to the Company's Tools](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-mcp-company-tools/README.md)
- Company monorepo template: [4Geeks Academy — AI Engineering Company Project Monorepo](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo)
- Required authentication project: [MCP Auth documentation](https://mcp-auth.dev/docs)
- Agent adapter named by the assignment: [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- MCP protocol specification: [Model Context Protocol](https://modelcontextprotocol.io/)

The 4Geeks assignment is authoritative for grading and project scope. External documentation is implementation support and must be reconciled with the versions pinned in the target monorepo.
