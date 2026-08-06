# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._

## Active services

| Service | Path | Purpose |
|---------|------|---------|
| HealthCore API (Phase 2) | [`api/`](api/) | FastAPI incident analyze + export endpoints; reuses [`incidents-analysis/`](../incidents-analysis/) |

```bash
cd services/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The full modular monolith described in [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) (`healthcore-api`) is still future work; `api/` is the first HTTP surface.

## Related CLI (not a service)

The patient incident CSV analyzer CLI remains under [`incidents-analysis/`](../incidents-analysis/). The API imports that package’s `src/` modules rather than copying rules.
