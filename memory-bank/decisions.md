# Decisions — Active iteration

Material decisions and rejected alternatives. Full backend rationale: [`docs/architecture_proposal.md`](../docs/architecture_proposal.md).

## Adopted

| Decision | Rationale |
|----------|-----------|
| Project memory bank uses global layout (`context`, `spec`, `progress`, `decisions`, `archive/`) | Aligns with global working rules in `~/.codex/AGENTS.md`; keeps active iteration concise |
| Prior monorepo-frontend memory archived dated `2026-07-29-monorepo-ai-frontend` | Iteration complete; durable facts retained in active files |
| Domain-driven **modular monolith** on **FastAPI** under `services/healthcore-api` | Fits six-person tech team; domain folders match org; extraction seams later |
| Backend becomes owner of Milestone 2 analytics (port to Python; TS `src/` legacy after parity) | PHI-adjacent ops analytics; non-TS consumers coming; avoid dual formulas |
| Data residency by **separate US/UK deployments + DBs**, shared codebase | HIPAA / UK GDPR; reject single-DB + region column |
| Separate Next.js frontends call API via HTTPS JSON + bearer scopes | Already two UIs; Next Route Handlers stay thin proxies |
| CI-enforceable domain import boundaries (planned with backend) | Prevent modular-monolith erosion at larger team size |

## Rejected (for now)

| Alternative | Why rejected | Reopen when |
|-------------|--------------|-------------|
| Microservices day one | Ops cost > benefit for current team | Proven scale/deploy split + owner |
| Node backend only to reuse TS `src/` | Future workers/agents/pipelines not TS-native | Unlikely; API ownership preferred |
| Single global DB with `region` column | Easy to query across jurisdictions by mistake | Compliance written exception for non-PHI only |
| GraphQL / gRPC / event bus initially | Premature complexity | Clear multi-client or async fan-out need |
| Financial-dashboard rule pack copied here | Wrong product/domain; user declined | N/A |

## Still provisional until implementation

- Exact OAuth scope matrix and first write endpoint ordering (proposal §10 recommends locations → analytics → writes).
- TS→Python migration window (proposal suggests ~two sprints after analytics endpoints ship).
