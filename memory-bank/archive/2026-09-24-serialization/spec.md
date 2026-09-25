# Spec — Active iteration

## Requirements

1. Memory bank follows global layout: `context.md`, `spec.md`, `progress.md`, `decisions.md`, and `archive/YYYY-MM-DD-name/` (with `implementation-plan.md` and `tech-updates.md` when archiving).
2. Root memory files stay limited to the **active** iteration plus standing facts. Completed work lives under `archive/`. Do not read `archive/` unless the user asks.
3. Agents update `progress.md` (and `decisions.md` when material) after milestones, scope changes, validation, blockers, or handoffs.
4. Delivery gates: scoped `.agents/rules/`, `skills/pre-delivery-verification` before UI/agent-doc commits, protected paths untouched without instruction.
5. Backend expansion follows [`docs/architecture_proposal.md`](../docs/architecture_proposal.md) (modular monolith under `services/healthcore-api`, region-split residency, API owns analytics).
6. **Testing and edge cases:** implementation and validation are one task. Add or update focused tests for new/changed behavior and bug fixes; prefer public interfaces; cover realistic edge cases; run the narrowest relevant checks first. Do not weaken tests to make the implementation pass. If a check cannot be run, state the limitation and what remains unverified. Docs-only changes need no runtime tests.
7. Shipped auth stays as documented in standing behavior below (TinyDB User/Profile, JWT bearer, `uis/web` localStorage, Resend reset). `uis/website` stays fully public. The AUTH course contract is archived — do not load it unless asked.
8. Error-handling is archived — do not load it unless asked. User-facing errors remain sanitized (no raw `detail`, stacks, or status codes in the UI), **except** outbound HTTP `400` insufficient-stock `detail`, which is shown inline as designed staff copy.
9. Bullet-proof test coverage is archived — do not load it unless asked. Run commands remain in [`TESTING.md`](../TESTING.md).
10. Milestone 5 inventory API is archived — do not load [`archive/2026-09-18-inventory-api/`](archive/2026-09-18-inventory-api/) unless asked. Durable notes: [`implementation-memory/inventory-api.md`](implementation-memory/inventory-api.md).
11. Milestone 5 Part 2 inventory UI is archived — do not load [`archive/2026-09-18-inventory-backoffice-ui/`](archive/2026-09-18-inventory-backoffice-ui/) unless asked. Durable notes: [`implementation-memory/inventory-backoffice-ui.md`](implementation-memory/inventory-backoffice-ui.md).
12. Docker Compose (`infra-40`) is archived — do not load [`archive/2026-09-23-docker-compose/`](archive/2026-09-23-docker-compose/) unless asked. Durable notes: [`implementation-memory/docker-compose-dev.md`](implementation-memory/docker-compose-dev.md).
13. Web Vitals is archived — do not load [`archive/2026-09-23-web-vitals/`](archive/2026-09-23-web-vitals/) unless asked. Durable notes: [`implementation-memory/web-vitals.md`](implementation-memory/web-vitals.md). Evidence remains in root `AUDIT.md`, `REPORT.md`, and `audit/`.
14. **Backend serialization:** audit every application-owned FastAPI route; explicit `response_model` (or documented special response); separate write vs public schemas; no secrets or unauthenticated email echo; list/detail/relationship shapes match [`uis/web`](../uis/web) consumers; trail in [`docs/serialization-audit.md`](../docs/serialization-audit.md).

## Acceptance criteria

- [x] Required memory-bank files exist at `memory-bank/` root.
- [x] Completed iterations archived: `2026-07-29-monorepo-ai-frontend`, `2026-08-28-supplier-directory`, `2026-08-28-staff-auth`, `2026-08-31-error-handling`, `2026-09-04-bullet-proof`, `2026-09-18-inventory-api`, `2026-09-18-inventory-backoffice-ui`, `2026-09-23-docker-compose`, `2026-09-23-web-vitals`.
- [x] Project `AGENTS.md` points at the global memory-bank file names.
- [x] AUTH-088 / API-042 / FE-019 implemented; results in [`TESTING.md`](../TESTING.md).
- [x] `BulletProofApp-Context.md` moved to `memory-bank/archive/2026-09-04-bullet-proof/`.
- [x] Milestone 5 inventory API: six authenticated `/inventory` routes, SQLModel persistence, seed, pytest, live `/docs` smoke; phase guide in `archive/2026-09-18-inventory-api/`.
- [x] Milestone 5 Part 2 inventory UI: four authenticated `/backoffice/inventory/...` views in `uis/web`; phase guide in `archive/2026-09-18-inventory-backoffice-ui/`.
- [x] infra-40 Compose stack: `ui` + `backend` on `healthcore_dev`; phase guide in `archive/2026-09-23-docker-compose/`.
- [x] Web Vitals audit: production Lighthouse loop on both Next apps; phase guide in `archive/2026-09-23-web-vitals/`.
- [x] `Backend-Serialization.md` at repo root for the next phase.
- [x] `docs/serialization-audit.md` lists every application endpoint with original classification, target fields, and final status.
- [x] Every JSON route has an explicit `response_model`; special 204/CSV routes have documented contracts.
- [x] Unauthenticated register/login/forgot/reset do not echo email; no password/hash/token leaks; `GET /auth/me` still returns the caller's email.
- [x] Write schemas cannot set server-managed fields; list/detail/relationship shapes match consumers.
- [x] Focused payload tests, full `uv run pytest`, three `/docs` checks, consumers still work.

## Interfaces / expected behavior (standing)

| Surface | Expected behavior |
|---------|-------------------|
| `uis/website` | Public corporate site; EN/ES via `hc_lang` cookie; enquiry form; brand blues; no auth |
| `uis/web` | Public `/login`, `/register`, `/forgot-password`, `/reset-password`; protected welcome, `/operations`, `/incidents`, `/suppliers`, `/backoffice/inventory/{products,orders,orders/inbound,orders/outbound}`, `/account/profile`, `/account/change-password` |
| `scripts/` | Phase 1 `analyze.py` + `incidents-healthcore.csv` |
| `services/api` | Incidents + suppliers (TinyDB) + staff auth + inventory (SQLModel). Login is `POST /auth/login`. `GET /health` public. Sensitive routes require bearer JWT. CORS from `CORS_ORIGINS` (default `http://localhost:3001`, `http://127.0.0.1:3001`). |
| Compose | `docker compose up` from repo root: website 3000, staff UI 3001, API 8000 on network `healthcore_dev` |
| Future `services/healthcore-api` | FastAPI `/api/v1` domains; OpenAPI contract for frontends |
| Agents | Skill discovery before non-trivial work; smallest change that satisfies the ask; no secrets; no git publish unless asked |

## Validation

- Code changes: follow requirement 6; report tests added/updated, commands run, results, and unverified risks.
- API: `uv run pytest` from `services/api`. Auth coverage: `uv run pytest --cov=app.auth`. Backoffice coverage: `--cov=app.routers.incidents --cov=app.routers.suppliers --cov=app.suppliers`. Inventory: `uv run pytest tests/test_inventory_products.py tests/test_inventory_orders.py tests/test_inventory_seed.py`. CORS: `uv run pytest tests/test_cors.py`.
- UI: `npm run typecheck`. Frontend helpers: `npm test -w uis/web`.
- Compose: `docker compose config`; `docker compose up --build`; host curls on 3000/3001/8000; `docker compose exec ui wget -qO- http://backend:8000/health`.
- Docs-only: confirm memory files present and `AGENTS.md` links resolve. No runtime test required.
- Real Resend delivery requires a local `RESEND_API_KEY` (not in git). Empty `DATABASE_URL` uses sqlite under `services/api/data/`.
- Optional one-time seed (system packages in the image, not host `.venv`): `docker compose exec backend python -m app.auth.seed` then `python -m app.inventory.seed`.
