# Implementation plan — Backend serialization audit

Audit and correct every HealthCore FastAPI success contract so responses are explicit Pydantic projections, not accidental ORM/dict dumps.

Phases: inventory and classify → correct auth contracts first → remaining warn/fail routes → tests and `/docs` smoke → mark audit rows compliant.

Stay in `services/api`. Do not build a new backend. Record original vs final state in `docs/serialization-audit.md`. Auth first: no email on public `POST /users`; keep email on `GET /auth/me`. Every JSON route gets `response_model` on the decorator; CSV export and DELETE 204 get documented special contracts.

Out of scope: framework `/docs`/`/redoc`/`/openapi.json`, auth/error redesign, endpoint renaming, frontend features, git publish unless asked.
