# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._

## Related (not a service)

The patient incident CSV analyzer is a **local Python CLI** under [`incidents-analysis/`](../incidents-analysis/). It is not an HTTP API and must not be placed here. Future dashboard integration may call similar rules from a `services/` module later.
