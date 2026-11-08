# Project Context: Support Agent with LangGraph — Part 1

## Document purpose

This file is the implementation brief for Cursor. It defines the scope, intent, constraints, acceptance criteria, and expected integration points for the 4Geeks Academy project **“Support Agent with LangGraph — Part 1 of 2: Migration and Agent Flow.”**

This is a planning and handoff document, not an implementation. Before changing code, Cursor must inspect the actual student monorepo and reconcile this brief with its existing structure, conventions, company briefing, RAG implementation, tests, and dependency versions.

## Source of truth

- Primary assignment source supplied for this analysis: [Support Agent with LangGraph — Part 1](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-langgraph-agent-base/README.md)
- Prerequisite project: [Milestone 7 — RAG & Knowledge Base](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-milestone-rag-knowledge-base/README.md)
- Base repository: [AI Engineering Company Project Monorepo](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo)
- Analysis date: 2026-11-07

If instructor guidance or the student's assigned `company-BRIEFING.md` conflicts with this file, those sources take precedence. Cursor should surface the conflict before implementing a materially different interpretation.

## Executive summary

The existing system already has a working company-specific RAG pipeline. It can prepare and embed a knowledge corpus, retrieve relevant chunks, generate a grounded answer, and expose that behavior through FastAPI. The problem is that the current `query()` flow is operationally opaque: it returns an answer but does not expose which steps ran, why routing decisions were made, or what intermediate state was produced.

The goal of this project is to **migrate the orchestration of that existing RAG behavior into a compiled LangGraph state graph**. The new graph must make the flow explicit, inspectable, independently testable, resumable through checkpointing, and traceable after execution. It must preserve the existing RAG behavior and company grounding. It must not rewrite the retrieval or embedding system from scratch.

This is **Part 1 of 2**. Part 1 establishes the graph foundation. External operational tools, such as incident or inventory lookup, belong to Part 2 and are out of scope here.

## Business and engineering problem

The company support assistant answers questions using an internal knowledge base built in the preceding RAG milestone. The answer may be correct, but the system currently behaves like a black box. A production owner cannot reliably answer:

- Which step received and validated the question?
- Did retrieval run?
- What context did retrieval produce?
- Why did the workflow generate an answer, decline to answer, or terminate?
- Can a failed or interrupted run be inspected and resumed?
- Can routing and grounding be evaluated without rerunning a live model every time?

The project solves that trust and operability gap by turning the implicit RAG sequence into an explicit graph of state, nodes, and conditional transitions.

## Existing system and required prerequisites

This assignment assumes the student's own company monorepo already contains the completed Milestone 7 RAG implementation. Before writing any code, Cursor must locate and verify the real implementation rather than inventing file paths or APIs.

The expected existing capabilities are:

- `setup()` prepares the company source documents and indexes semantic chunks.
- `embed()` creates embeddings using a dedicated embedding model.
- `retrieve()` queries the existing vector knowledge base, applies a similarity threshold, and returns payload dictionaries rather than raw database objects.
- `generate_answer(question, context)` assembles the grounded prompt and calls the generation model.
- `query()` composes retrieval and generation for the legacy RAG path.
- A FastAPI endpoint, commonly `POST /knowledge/query`, exposes the legacy query behavior.
- Existing RAG tests validate retrieval, generation, threshold behavior, and grounding.
- The company corpus and domain rules are defined by the assigned `company-BRIEFING.md` and documents under `docs/company-knowledge-base/` or the repository's equivalent path.

The likely locations from the syllabus are:

```text
data/
  process/                     # Existing corpus preparation/indexing
  pipelines/                   # Existing retrieve/query/generation functions
  eval/                        # Existing RAG evaluation data

docs/
  company-knowledge-base/      # Existing company source documents
  rag/                         # Existing RAG design notes

services/                      # Existing FastAPI service/router code
tests/
  pipelines/                   # Existing RAG tests; new agent evals belong here
```

These paths are indicative. Cursor must follow the actual repository structure and import conventions.

If the prerequisite RAG functions or tests do not exist, are incomplete, or do not expose generation separately from retrieval, Cursor must report that prerequisite gap before proceeding. The narrow compatibility refactor permitted by this assignment is to extract or adapt `generate_answer(question, context)` so the graph can call generation with already-retrieved context. The RAG system itself must not be redesigned.

## Primary objective

Create a LangGraph-based support-agent flow that:

1. Receives and validates a user question.
2. Retrieves relevant company knowledge by reusing the existing `retrieve()` function.
3. Routes based on explicit state and output conditions.
4. Generates a final grounded answer by calling the existing generation step with the retrieved context.
5. Produces an honest no-context response when retrieval finds nothing sufficiently relevant.
6. Is compiled before it can be executed.
7. Checkpoints meaningful state transitions.
8. Persists a queryable trace for every run.
9. Is exposed through a thin FastAPI endpoint.
10. Has runnable evaluations for routing, trace correctness, and answer grounding.

## Required behavior

### 1. Explicit, minimal graph state

Define a typed state containing only information needed by downstream nodes and routing decisions. A reasonable conceptual state is:

| Field | Purpose | Notes |
| --- | --- | --- |
| `question` | Normalized user question | Required after input validation |
| `retrieved_context` | Context returned by the existing retriever | Use the repository's real payload type; do not store raw vector-client objects |
| `answer` | Final generated or honest fallback answer | Empty until a terminal answer node runs |
| `error` or `status` | Structured failure/routing signal, if needed | Keep minimal; do not expose internal details to clients |

Run IDs, thread IDs, timestamps, and trace metadata should be handled by the graph/checkpointer/tracing layer where possible rather than inflating business state.

Do not include full conversation history unless the repository has a concrete, documented requirement for multi-turn behavior. This project is a question-to-answer flow, not a conversational-memory milestone.

### 2. Single-responsibility nodes

At minimum, model these responsibilities as separate nodes:

- **Receive/validate question:** Accept and normalize input; detect empty or invalid questions.
- **Retrieve context:** Call the existing `retrieve()` exactly once for the valid question and store its result in state.
- **Generate grounded answer:** Call `generate_answer(question, retrieved_context)` using context already produced by the retrieval node.
- **No-context fallback:** Return an honest response such as “I don't have information about that” without inventing company facts.

An explicit error/failure node may be added if it simplifies consistent error handling, but unnecessary nodes and abstractions should be avoided.

### 3. Real conditional routing

The graph cannot be only a hardcoded straight sequence. It must include meaningful conditional edges based on node output or state. At minimum:

- Empty or invalid question → terminate with a clear validation response or route to an error/fallback node; do not run retrieval.
- Valid question → retrieval node.
- Retrieved context above the existing relevance threshold → generation node.
- No relevant context → honest no-context node; do not force generation on empty/irrelevant context.
- Terminal answer or handled error → `END`.

Routing should be deterministic and independently testable. Do not ask the LLM to decide conditions that can be decided from explicit state.

### 4. Preserve retrieval/generation separation

This is a hard acceptance constraint:

- The retrieval node calls the existing `retrieve()` function.
- The generation node calls the existing `generate_answer(question, context)` function with the context already stored in graph state.
- No node may call the original monolithic `query()` if doing so causes retrieval to run again.
- No node may combine retrieval and generation in a way that makes those steps opaque again.
- If `query()` is reused for compatibility, it must support already-retrieved context and skip internal retrieval. Prefer calling the factored generation function directly.

The graph is an orchestration layer around working RAG components, not a replacement for them.

### 5. Compile before execution

Build and compile the graph during application initialization or another explicit setup phase before handling a request. Execution paths must invoke the compiled graph, not construct an ad hoc graph per request.

Structural mistakes—such as missing entry/terminal paths, unconnected nodes, invalid transitions, or incompatible state contracts—must fail clearly during startup/build/test rather than appearing as a production request failure.

Use the LangGraph API compatible with the repository's locked dependency version. Do not assume an API from memory; inspect the installed/locked version and current official documentation before implementation.

### 6. Checkpointing

Configure a LangGraph-compatible checkpointer so meaningful transitions are persisted and a run can be inspected or resumed. At least one state transition must have verifiable checkpoint data, but the intended design is checkpointing across the graph's meaningful execution steps.

Requirements:

- Each run must have a stable run/thread identifier.
- Checkpoint configuration must be supplied consistently by the service layer.
- Tests must not rely on shared mutable checkpoint state from unrelated runs.
- The implementation should use a test-friendly local/in-memory option where appropriate and a durable repository-aligned option for normal execution if the project already has persistence infrastructure.
- If only an in-memory checkpointer is used, document its process-lifetime limitation and confirm with the instructor whether it satisfies “resumed” for this assignment.

Do not introduce a major new database solely for checkpointing without evidence that the repository or assignment requires it.

### 7. Queryable tracing

Every graph run must produce a trace that can be queried after the run. Printing lines to stdout is not sufficient.

The trace must make it possible to determine:

- A stable run identifier.
- Which nodes executed.
- The order in which they executed.
- The meaningful output or state change produced by each node.
- Whether the run completed, took a fallback route, or failed.
- Enough information to evaluate routing and grounding without rerunning the live workflow.

Acceptable approaches include:

- LangSmith, if the student has configured access; or
- Structured trace events persisted to a queryable local/project store or file format that tests can load by run ID.

Never persist secrets, credentials, authorization headers, raw exception stack traces, or unnecessary personal/sensitive data in traces. If retrieved company content may be sensitive, store only what is needed for the assignment's evaluation or store references/hashes plus approved excerpts according to project conventions.

### 8. FastAPI endpoint

Expose the compiled graph through a service endpoint, commonly:

```http
POST /agent/query
Content-Type: application/json

{
  "question": "..."
}
```

The exact response schema should follow existing service conventions. At minimum it must return the final answer. Returning a non-sensitive run ID is recommended so the corresponding trace can be inspected, but do not expose raw retrieved chunks, similarity scores, checkpoints, or internal stack traces unless the existing API contract explicitly requires them.

The endpoint must:

- Validate its request using the repository's established Pydantic/FastAPI patterns.
- Invoke the already-compiled graph.
- Supply a unique/stable run or thread identifier needed by checkpointing/tracing.
- Contain no retrieval, prompt, generation, or routing business logic.
- Convert known failures into clear, safe HTTP responses.
- Never return a raw stack trace or leak implementation details.

The new endpoint may replace or coexist with the existing RAG endpoint. Preserve the existing endpoint unless the assignment, instructor, or repository explicitly requires removal.

## Grounding and company-specific behavior

The migration must preserve the behavior established by Milestone 7:

- Retrieval uses the existing company vector collection and similarity threshold.
- Answers use only the retrieved company context.
- The generation model preserves the voice, audience, and business priorities in `company-BRIEFING.md`.
- When no relevant context is found, the agent admits that it lacks sufficient information.
- Raw vector hits are never returned as the answer.
- Embedding and generation remain separate model responsibilities.
- Existing source metadata and company-specific field names remain intact.

At least one evaluation must prove that a known question returns the expected company fact or entity from the briefing/knowledge corpus. A correct graph route with an ungrounded answer is a failed implementation.

## Testing and evaluation requirements

### Existing tests

All existing RAG tests must continue to pass. The new agent evaluations extend those tests; they do not replace them.

### New evaluations

Add at least three agent evaluations under `tests/pipelines/`, runnable with one documented command. The assignment describes these as evals against recorded trace data, not as repeated live end-to-end LLM executions.

The suite must include at least:

1. **Valid grounded path:** A known company question runs receive/validate → retrieve → generate in the correct order and produces the expected verifiable company fact/entity.
2. **Empty input path:** Empty or whitespace-only input does not call retrieval or generation and terminates with a clear validation/fallback result.
3. **No-context path:** Retrieval returns no chunks above the threshold, generation is not forced, and the trace shows the no-context fallback route.

Recommended additional coverage:

- Retrieval is called exactly once per valid run.
- Generation receives the exact context produced by retrieval.
- The graph object is compiled before invocation.
- Checkpoint state exists for a known run/thread ID.
- A node failure becomes a safe API error without a stack trace.
- Separate concurrent run IDs do not leak state or checkpoints into one another.
- Trace lookup by run ID returns ordered events from a completed fixture.

Tests should mock or stub external systems where appropriate:

- No live generation model should be required for routine CI.
- No live Qdrant instance should be required for focused graph/routing tests.
- LangSmith should not be mandatory for local unit tests if it requires external credentials.
- Existing repository test conventions and fixtures should be reused.

The exact commands must be derived from the actual project. The assignment requires the agent evals to be runnable with a single command, for example a focused `pytest` invocation covering `tests/pipelines/`.

## Error handling expectations

- Invalid/empty questions are handled intentionally and do not start retrieval.
- No-context retrieval is a normal business outcome, not an exception.
- Retriever, generation provider, checkpointer, or tracing failures are caught at the correct boundary.
- Client responses are clear and non-sensitive.
- Internal errors may be logged/traced safely for debugging, but raw stack traces are never returned over HTTP.
- Failure behavior must be visible in the trace when trace persistence itself is still available.
- Do not silently fabricate an answer when a dependency fails.

## Repository placement

Use the existing monorepo, not a new repository. The intended high-level placement is:

```text
data/
  pipelines/                    # Existing RAG functions; reuse, do not duplicate

services/
  <existing-or-agent-service>/  # Graph state, nodes, routing, compilation, endpoint

tests/
  pipelines/                    # Agent trace/routing/grounding evals
```

Prefer the service/package that already owns the FastAPI knowledge endpoint. Avoid creating a second application or duplicating dependency/bootstrap configuration unless the repository architecture clearly requires a separate service.

## Dependencies and configuration

- Add LangGraph using the repository's required package workflow: `uv add langgraph`.
- Do not use `pip install` or Pipenv.
- Preserve the project's lockfile and dependency conventions.
- Reuse existing provider, Qdrant, model, and service configuration.
- Keep secrets in the existing environment/configuration mechanism; never hardcode them.
- If LangSmith is selected for tracing, document the required environment variable names but never commit their values.
- Do not upgrade unrelated dependencies as part of this work.

## Explicit non-goals

The following are outside the scope of Part 1 unless separately required by the actual repository or instructor:

- Rewriting `setup()`, `embed()`, `retrieve()`, or the vector database integration.
- Re-chunking or re-indexing the company corpus merely because LangGraph is being added.
- Replacing Qdrant or changing embedding/generation providers.
- Building a new RAG system or new repository.
- Adding incident, inventory, CRM, web-search, or other external tools; those belong to Part 2.
- Adding MCP integration; that is a later project.
- Adding persistent conversational memory or self-improvement; those are later milestones.
- Adding multi-agent delegation.
- Building or redesigning a frontend unless needed for an existing endpoint contract.
- Returning chain-of-thought or hidden model reasoning. “Traceable reasoning flow” here means observable graph steps, routing, inputs/outputs, and state transitions—not private model chain-of-thought.
- Removing the existing `/knowledge/query` endpoint without an explicit requirement.
- Large unrelated refactors, infrastructure changes, or dependency upgrades.

## Implementation approach for Cursor

Cursor should proceed in this order after receiving the actual repository:

1. Read root and directory-level instructions (`AGENTS.md`, `README.md`, repository rules, and memory bank).
2. Read the assigned `company-BRIEFING.md` and identify the grounding fact(s) suitable for evaluation.
3. Locate the current RAG pipeline, generation function, knowledge endpoint, tests, dependency files, and service bootstrap.
4. Run the existing focused RAG tests before changes and record the baseline.
5. Document the actual imports, types, payload shape, threshold behavior, and endpoint conventions.
6. Design the smallest compatible graph state and node contracts.
7. Choose checkpoint and trace persistence consistent with available infrastructure and testability.
8. Add focused tests/evals first or alongside implementation, including regression coverage for empty input and no-context routing.
9. Implement graph nodes and conditional edges by wrapping existing functions.
10. Compile the graph during startup/module initialization and expose it through the thin endpoint.
11. Run focused graph/eval tests, existing RAG tests, then applicable lint/type/build checks.
12. Capture evidence for submission: at least one full trace and the eval output.

Cursor must not guess company-specific values or silently compensate for missing prerequisite work. Any material prerequisite gap should be reported with the exact file/function that is absent or incompatible.

## Acceptance criteria / definition of done

The work is complete only when all applicable items below are verified:

- [ ] Work is performed in the student's existing company monorepo on the requested feature branch, not in a new repository.
- [ ] `langgraph` is added with `uv` and recorded in the project's dependency/lock files.
- [ ] Graph state is typed, minimal, and explicit.
- [ ] Receive/validation, retrieval, generation, and no-context behavior have clear single-responsibility nodes.
- [ ] At least one real conditional route is implemented; empty input and no-context outcomes do not follow the normal generation path.
- [ ] The retrieval node reuses the existing `retrieve()` function.
- [ ] The generation node reuses the existing factored generation function with previously retrieved context.
- [ ] No node re-runs retrieval by wrapping the monolithic `query()` flow.
- [ ] The graph is compiled before request execution.
- [ ] Meaningful graph state is checkpointed and verifiable by run/thread ID.
- [ ] Every run produces a persisted, queryable, ordered trace.
- [ ] A thin FastAPI endpoint invokes the compiled graph and contains no business logic.
- [ ] API failures produce safe, clear responses without raw stack traces.
- [ ] At least three runnable evals exist in `tests/pipelines/`.
- [ ] Evals verify trace/routing behavior rather than relying exclusively on final-answer string matching.
- [ ] At least one eval proves the answer remains grounded in the existing company briefing/knowledge base.
- [ ] Existing RAG tests still pass.
- [ ] No secrets or sensitive internal details are exposed through API responses or traces.
- [ ] No Part 2 tools or later-milestone features are introduced.
- [ ] Validation commands and actual results are documented.
- [ ] Submission evidence includes a screenshot/export of one complete trace and console/file output from the eval run.

## Submission expectations

The assignment treats this as an independent **Part 1 pull request**.

- Recommended branch: `feature/langgraph-agent-base`
- PR target: the original student/company monorepo's main branch, following course instructions
- Required label: `langgraph-agent-base`
- PR evidence:
  - Screenshot or export of at least one complete trace
  - Output from running the evaluations

Part 1 should be reviewed independently even if Part 2 later builds on the same graph foundation. After approval, merge Part 1 into `main` before beginning later work so future branches are not based on outdated code.

## Open questions Cursor must resolve from the repository

These details cannot be determined from the generic assignment and must be discovered before implementation:

1. What is the assigned company, audience/voice, and exact grounding fact from `company-BRIEFING.md`?
2. Where are `retrieve()`, `query()`, and `generate_answer()` actually defined, and what are their real signatures/types?
3. Does `generate_answer()` already exist as a separately importable function?
4. What is the retrieved context payload schema?
5. Which FastAPI app/router currently owns `/knowledge/query`?
6. What response/error schemas and dependency-injection conventions does the service use?
7. Which LangGraph version will `uv` resolve or is already locked, and which checkpoint APIs are supported by that version?
8. Is LangSmith available, or should traces use a repository-local structured store?
9. What persistence technology already exists and is appropriate for durable checkpoints/traces?
10. What commands run focused tests, all relevant tests, type checks, linting, and service startup?
11. Are there existing trace/audit models that should be reused?
12. Must `/agent/query` coexist with `/knowledge/query`, or has the instructor requested replacement?

These are discovery tasks, not permission to broaden the project. Resolve them by inspecting the repository and current instructions before making changes.

