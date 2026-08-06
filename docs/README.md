# `docs` folder

This folder holds **cross-cutting documentation** for the monorepo: architecture guides, technical decisions, conventions, processes, and any material shared across applications, pipelines, agents, and workflows.

- **Main purpose**: provide a single place for “global” project documentation (not tied to one app or agent only).
- **Recommendation**: organize docs by topic (architecture, deployment, data, security, observability, etc.) and keep links from each component’s README to these guides.

> _Spanish version: [README.es.md](./README.es.md)._

## Architecture

| Document | Purpose |
|----------|---------|
| [architecture_proposal.md](architecture_proposal.md) | Backend architecture proposal for HealthCore Digital — modular monolith on FastAPI, domain layout, technical decisions, compliance/residency, risks, and deliberately deferred choices. **No code;** read before implementing `services/`. |
