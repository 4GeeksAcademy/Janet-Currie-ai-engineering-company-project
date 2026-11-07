# Decisions — Active iteration

Standing decisions that still constrain work. Completed-iteration snapshots: [`archive/2026-07-29-monorepo-ai-frontend/`](archive/2026-07-29-monorepo-ai-frontend/), [`archive/2026-08-28-supplier-directory/`](archive/2026-08-28-supplier-directory/), [`archive/2026-08-28-staff-auth/`](archive/2026-08-28-staff-auth/), [`archive/2026-08-31-error-handling/`](archive/2026-08-31-error-handling/), [`archive/2026-09-04-bullet-proof/`](archive/2026-09-04-bullet-proof/), [`archive/2026-09-18-inventory-api/`](archive/2026-09-18-inventory-api/), [`archive/2026-09-18-inventory-backoffice-ui/`](archive/2026-09-18-inventory-backoffice-ui/), [`archive/2026-09-23-docker-compose/`](archive/2026-09-23-docker-compose/), [`archive/2026-09-23-web-vitals/`](archive/2026-09-23-web-vitals/), [`archive/2026-09-24-serialization/`](archive/2026-09-24-serialization/), [`archive/2026-09-30-caching-optimisation/`](archive/2026-09-30-caching-optimisation/), [`archive/2026-10-14-telemetry/`](archive/2026-10-14-telemetry/), [`archive/2026-10-21-data-pipeline/`](archive/2026-10-21-data-pipeline/), [`archive/2026-11-04-background-processes/`](archive/2026-11-04-background-processes/), [`archive/2026-11-04-message-queue/`](archive/2026-11-04-message-queue/), [`archive/2026-11-05-sales-forecast-model/`](archive/2026-11-05-sales-forecast-model/), [`archive/2026-11-07-regression-model-eval/`](archive/2026-11-07-regression-model-eval/). Architecture rationale: [`docs/architecture_proposal.md`](../docs/architecture_proposal.md). Course/phase guides live in their archives (do not load unless asked).

## Adopted

| Decision | Rationale |
|----------|-----------|
| Project memory bank uses global layout (`context`, `spec`, `progress`, `decisions`, `archive/YYYY-MM-DD-name/` with plan + tech-updates) | Aligns with global working rules; keeps active files concise |
| Finished course contracts and phase guides live in `archive/`, not repo root or the four active files | AUTH, error-handling, bullet-proof, inventory API, inventory UI, Docker Compose, Web Vitals, serialization, caching, telemetry, data-pipeline, background-processes, message-queue, and sales-forecast guides moved there after completion |
| AUTH-088 uses pytest + pytest-cov via `uv` in `services/api`; coverage is measured on `app.auth` | Course requires `uv run pytest --cov`; existing unittest files still run under pytest |
| AUTH-088 skips Jest for auth crypto; FE-019 adds Jest in `uis/web` for `apiClient` helpers | `authApi.ts` is fetch-only; token storage, `messageForStatus`, `toUserMessage`, and `parseError` are the testable utilities |
| API-042 extends existing incident/supplier unittest files rather than rewriting them as pytest functions | Smallest change; pytest already collects unittest.TestCase |
| FE-019 Jest lives only in `uis/web` via `next/jest` | Path aliases; public-site `enquiryValidation` would need a second Jest root |
| User-facing API errors go through `toUserMessage` / status maps, never raw `detail` or `Error.message` | Course forbids stack traces, status codes, and parse errors in the UI |
| FastAPI unhandled exceptions return a fixed 500 JSON body; logs stay server-side | Prevents traceback/secret leaks to clients |
| Website enquiry form stays client-only (no new enquiry API) | Wiring persistence would be a new feature |
| Implementation and validation are one task (proportional tests, realistic edge cases, report unverified risks) | Cursor `.cursor/rules/global-working-rules.mdc` and `AGENTS.md`; docs-only work needs no runtime tests |
| Domain-driven **modular monolith** on **FastAPI** under `services/healthcore-api` | Fits six-person tech team; extraction seams later |
| Backend becomes owner of Milestone 2 analytics (port to Python; TS `src/` legacy after parity) | PHI-adjacent ops analytics; avoid dual formulas |
| Data residency by **separate US/UK deployments + DBs**, shared codebase | HIPAA / UK GDPR |
| Separate Next.js frontends call API via HTTPS JSON + bearer scopes | Two UIs; Next Route Handlers stay thin proxies |
| Company briefing lives at root `CONTEXT.md`; Milestone docs under `docs/` | Programme README structure |
| Incident analyzer CLI lives under `scripts/` | Course submission monorepo layout |
| Phase 2 HTTP surface is `services/api` with UI in `uis/web` | Course paths |
| Supplier directory uses TinyDB at `services/api/data/suppliers.json` + Pydantic v2 | Milestone 09; seed via `uv run seed` |
| Supplier UI lives in `uis/web` (not `uis/backoffice`) | Internal app is `uis/web` |
| Auth lives in existing `services/api`; users/profiles only in TinyDB `data/auth.json` | Course forbids User/Profile in Postgres/Supabase |
| Login is `POST /auth/login` (`username` = email); JWT `sub` is TinyDB user id; token in `localStorage` | Course AUTH-01/02 |
| Roles are `admin` \| `manager` \| `user`; `POST /users` always `user` | Course AUTH-01 enum |
| Password reset uses signed JWT + TinyDB `password_resets`; email via **Resend** | Single-use `jti`; AUTH-03 |
| `uis/web` AuthGuard is client-side (`GET /auth/me`) | Middleware cannot read `localStorage` |
| `cryptography` pinned to `>=42,<45` | 45+ failed to compile on this Mac without OpenSSL/pkg-config |
| Inventory lives in SQLModel on `DATABASE_URL`; users stay TinyDB; `user_uuid` is `str(TinyDB id)` | HCR-0188; no UUID user key in this repo |
| Inventory pytest uses temp SQLite; Postgres `SELECT FOR UPDATE` on outbound | Isolation without secrets; SQLite does not row-lock |
| Inventory UI reuses `NEXT_PUBLIC_API_BASE_URL` (no `NEXT_PUBLIC_INVENTORY_API_URL`) | Same origin as incidents/suppliers/auth; default `http://localhost:8000` |
| Browser URLs include `/backoffice/inventory/...` with no Next `basePath` | Assignment URLs; app already lives at site root on port 3001 |
| Outbound HTTP `400` whose `detail` starts with `Insufficient stock for supply` is shown inline | Designed staff message / evaluator check 7; other errors still use `toUserMessage` |
| `apiFetch` rethrows caller-aborted signals and maps timeout abort to `ApiTimeoutError` | Consumption form must ignore stale `getSupply` without treating it as a timeout |
| Stock bands 0 / 1–24 / 25+ are presentation-only | Official stock is API `current_stock`; seed gloves (105) stay healthy |
| Inventory UI lives in `uis/web`, not `uis/backoffice` | Internal app is already the Next.js backoffice |
| Compose application DNS names stay `ui` and `backend` | infra-40; DEV-55 extra services do not rename them |
| Compose `build.context` is repo root even though Dockerfiles live under `uis/` and `services/` | Root npm lockfile and `scripts/` (`parents[3]` from `app/main.py`) are outside those folders |
| Browser `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` | All `uis/web` API calls are client-side `fetch`; Docker DNS `http://backend:8000` would break the host browser |
| CORS origins from `CORS_ORIGINS` (comma-separated), defaulting to the two localhost:3001 values | Brief requires config; no wildcard-with-credentials |
| `requirements.txt` is exported/kept in sync with `pyproject.toml` (includes `sqlmodel`, `psycopg[binary]`) without `-e .` | Docker `uv pip install --system -r requirements.txt` cannot install the local package path |
| Named volumes for `node_modules` and `/app/services/api/.venv` | Host bind mounts must not hide image deps or overwrite the Mac host `.venv` |
| Uvicorn `--reload-dir app` plus `WATCHFILES_FORCE_POLLING=true` | Watching the whole `services/api` tree reloaded on `.venv` writes; native WatchFiles on Docker Desktop macOS can stall the worker |
| Container seed is `python -m app.auth.seed` (system site-packages), not `uv run seed-auth` | `uv run` inside the bind mount created a Linux `.venv` on the host |
| Web Vitals audits use host `next build` + `next start`, not Compose `next dev` | Comparable lab scores; brief forbids mixing `dev` baseline with production after |
| Staff Lighthouse target is `uis/web` `/operations`, not leftover `uis/backoffice` | Internal app is already the Next.js backoffice on port 3001 |
| Optional Lighthouse skills are not installed unless the user authorizes them | Brief makes install optional; user rule forbids creating/installing skills without permission |
| Website below-fold sections are Server Components; `hc_lang` cookie + `router.refresh()` for ES | Shrinks the hydrated tree (W1) without duplicating EN/ES markup; `next/dynamic` of those sections delayed LCP and was dropped |
| Appointment modal is client-only after open | Not in LCP; avoids shipping the form on first load |
| Staff role label uses `text-slate-600` | Lighthouse color-contrast on `#94a3b8` / white failed 2.56:1 |
| Serialization audit stays in `services/api` with existing Pydantic v2 modules | Brief forbids a new backend; schemas already live in `auth/models.py`, `inventory/schemas.py`, `suppliers/models.py` |
| Public `POST /users` must not echo email; `GET /auth/me` may | Evaluator rule 9 vs profile consumer `fetchMe` |
| Do not slim supplier list fields that `SupplierDirectory` renders | notes, compliance, currency, `updated_at` are shown in the table |
| Public register returns `UserRegisteredResponse` (`id`, `role`, `is_active`) | Drop email on unauthenticated `POST /users`; `registerRequest` ignores the body |
| Incident analyze uses `IncidentAnalysisResponse`; export is documented `text/csv` | Untyped `dict` leaked in OpenAPI as `object` / fake JSON |
| FastAPI 0.141 route audit walks `_IncludedRouter.original_router` | `app.routes` no longer flattens included `APIRoute`s |
| Caching uses in-process TTL, not Redis | Cache decision stands; DEV-55 Redis is broker/result only (`db 0`), never the inventory cache |
| Compose services are `ui` + `backend` on named network `healthcore_dev` | infra-40 contract; `backend` is the DNS name other containers use. DEV-55 **adds** `redis`, `worker`, `flower` without replacing these |
| Do not cache `/health`, writes, auth/me, profiles, or incident CSV | Personalized, mutating, or upload/export payloads are unsafe or not reusable |
| Do not recount website `AppointmentModal` as a new lazy-load | Already `next/dynamic`; homepage below-fold dynamic imports delayed LCP |
| Cache `GET /inventory/products` and `GET /inventory/orders` (plus product-by-id) | Profiled: products miss ~106 ms from 1+2N stock queries; orders join/serialize |
| Reject `GET /suppliers` at current TinyDB volume | ~10 ms; filter-key invalidation cost exceeds benefit |
| TTL 30 s plus write invalidation | Staff freshness after movements; TTL covers missed invalidation / out-of-band SQL |
| Cache keys omit user/token/email | Catalogue payloads do not vary by staff identity |
| Lazy-load `OperationsAnalytics` and `IncidentAnalyzer` | Route-only heavy islands; production page JS 1.43–1.44 kB vs static `/suppliers` 4.46 kB |
| `useMemo` on `deriveMovementRows` in MovementHistory | Pure sort/label of expanded movement lists; not the existing supplier filter |
| Telemetry `event_type` values come from HealthCore plan/schemas, not README placeholders | Capture assignment forbids generic names |
| Single public `track()`; ingest URL from `NEXT_PUBLIC_TELEMETRY_ENDPOINT` | Tech-lead: no scattered fetch; stub URL swappable later |
| Stub `POST /telemetry/events` is unauthenticated | `sendBeacon` cannot attach JWT; payloads are allowlisted and non-PII |
| Inbound `unit_cost` (`> 0`); `event_cost = unit_cost × quantity` | Capture had no cost; inventory has no price; do not add a new event type |
| Reporting `clinic_id` is `"1"`…`"12"` | Existing inventory clinics; do not invent `austin-north` slugs |
| Reporting HTTP lives in `services/api` (`app/reporting` + `/reporting`) | One FastAPI app; ETL stays in `data/pipelines/` |
| Manual pipeline POST is a Celery producer (`202` + `task_id`) | DEV-55; ETL runs in the worker via `execute_monthly_clinic_supply_performance`; HTTP 409 from in-process lock dropped |
| Celery app is `app.celery_app` under `services/api` | Image WORKDIR and mounts do not include a top-level `services.celery_app` |
| DEV-55 DLQ is SQLModel `dead_letter_tasks` on `DATABASE_URL` | No Alembic; same engine as inventory; tests use temp SQLite |
| Celery `max_retries=3` means four executions | Assignment wording vs Celery retries; attempt_number = retries + 1 |
| `GET /tasks/{task_id}` is JWT like reporting; unknown IDs are `pending` | No per-user task registry; reporting is already any-staff |
| Currency from `country` only; never convert USD/GBP | HealthCore v1; FX is v2 |
| Prefect `>=3` via `uv` in `services/api` | Existing backend toolchain; Docker uses `requirements.txt` |
| API/CLI run ETL through `execute_monthly_clinic_supply_performance` (task `.fn()`) | Avoids starting an ephemeral Prefect server on each HTTP POST or pytest |
| Reporting warehouse is PostgREST `reporting` schema, not inventory SQLite | Same host as `telemetry_events`; tests use injectable fakes |
| Sprint 3 subflows wrap existing `@task`s; HTTP/CLI stay on `execute_…` | Avoids Prefect ephemeral-server hang in pytest and FastAPI |
| Isolated pipeline tests live at repo-root `tests/pipelines/` | Assignment path; no DB/API; run via `uv --directory services/api run pytest ../../tests/pipelines/test_pipeline.py` |
| Clinic-supply dashboard is `uis/web` `/backoffice/reporting/...` | No `uis/backoffice` app; same pattern as inventory |
| USD and GBP rendered in separate dashboard sections | Never show a cross-currency total |
| DEV-53 `job_runs` lives in PostgREST `reporting`, not inventory SQLModel | Same host as `telemetry_events` / `pipeline_runs`; tests use injectable fakes |
| DEV-53 trigger is a version-controlled host crontab example, not a Compose worker | infra-40 stays two services; do not install cron until authorized |
| Nightly job invokes `data/pipelines/pipeline.py` with no date flag | Handoff forbids inventing CLI semantics; CSV day ≠ pipeline month window |
| Nightly lock is a partial unique index on `status = 'processing'` | Assignment lock is the processing row; no advisory/Redis/in-process mutex |
| Documented cron is `0 2 * * *` in UTC | Proposed low-traffic default; documentation only until install is authorized |
| Sales forecast uses rolling one-month-ahead (Game A) | Briefing asks for coming months and lag features; not a frozen 24-month origin |
| Sales-forecast go/no-go is a report card, not a dollar cutoff | Briefing has no numeric threshold; lose-to-baseline MAE means no |
| Ranking Gini on continuous `revenue_usd`; K2 is D’Agostino–Pearson on residuals | User-supplied metric definitions; K2 is not R² |
| PSI is on `visits_count` train vs test | File has only `consolidated` rows; do not invent US/UK mix |
| Final estimator is `RandomForestRegressor` with seed 42 | Small n, Finance explainability, no extra XGBoost dependency |
| Isolated `uv` project under `scripts/sales_forecast/` | Do not pollute API pyproject or stdlib incident-analyzer requirements |
| Same-month `visits_count` and `avg_revenue_per_visit_usd` are not features | Near-identity leakage with the revenue target |
| Regression evaluation uses MAE as the primary metric | `CONTEXT.md` does not rank over-prediction against under-prediction; the forest was already selected with MAE |
| Fit diagnosis uses five expanding validation years, 2019–2023 | Matches the existing year-fold helper and keeps each check inside one calendar year |
| Overfitting when the 2022–2023 gap ratio is at least 0.50 | The gap has to remain large after more history; in-sample forest error is not enough by itself |
| Evaluation reads frozen settings from `metrics.json` and does not search | 100 / depth 5 / `min_samples_leaf` 2 / seed 42; a mismatch stops the run |
| 2024–2025 stay out of the fit verdict | The holdout remains isolated; the 2022–2023 side score is only a limitation |
| Learning curve is two MAE lines under `data/eval/sales_forecast/` | No shaded band on a single chronological series; fold spread stays in the table |
| Sample standard deviation divides by n − 1 | Five fold scores are a sample; the report names that choice |

## Rejected (for now)

| Alternative | Why rejected | Reopen when |
|-------------|--------------|-------------|
| Microservices day one | Ops cost > benefit for current team | Proven scale/deploy split + owner |
| Node backend only to reuse TS `src/` | Future workers/agents not TS-native | Unlikely |
| Single global DB with `region` column | Easy to query across jurisdictions by mistake | Compliance exception for non-PHI only |
| GraphQL / gRPC / event bus initially | Premature complexity | Clear multi-client or async fan-out need |
| Cookie / server-session auth | Course requires JWT bearer + `localStorage` | N/A |
| SendGrid for reset email | Resend selected | Provider change requested |
| Access-token revocation on password change | Needs denylist or `password_changed_at` | If session kill-switch is required |
| Rate limits / HTML email / reset audit logs | AUTH-03 extras; not approved | User asks |
| Jest for `uis/website` enquiry validation in FE-019 | Different app; extra Jest setup; ticket met by `apiClient` helpers | User asks |
| `NEXT_PUBLIC_INVENTORY_API_URL` | Would duplicate `apiBaseUrl()` | Never, unless inventory is hosted separately |
| Inventory UI in leftover `uis/backoffice` | Empty `.next` only; staff app is `uis/web` | Never |
| Postgres or mail containers in the dev stack | Brief is two application services; extras already exist as Supabase/Resend | User asks |
| `NEXT_PUBLIC_API_BASE_URL=http://backend:8000` | Host browser cannot resolve Compose DNS | Never for public Next vars |
| Dockerfiles under `infra/` | Placeholder only; brief pins `uis/Dockerfile` and `services/Dockerfile` | Never for infra-40 |
| `next/dynamic` for website below-fold sections | Delayed LCP; mobile Performance did not rise | Keep Header/Hero eager; ship sections as server children |
| Dual EN/ES markup hidden with CSS | Doubled HTML and delayed LCP | Cookie-selected single language |
| Redis as inventory/HTTP cache | Cache stays in-process TTL; DEV-55 Redis is broker-only | Measured multi-worker stale catalogue reads |
| `services/celery_app.py` as suggested by the assignment sample | Package and Docker WORKDIR are `app` under `services/api` | Never unless the image layout changes |
| Cache `GET /health` or `GET /auth/me` | Health is cheap; me is personalized | Never for `/auth/me` |
| Separate `services/reporting` process | Would duplicate the FastAPI app; use `app/reporting` instead | If a second service is explicitly required |
| Clinic slugs such as `austin-north` | Not in this repo; numeric clinic ids already exist | If clinics gain stable public slugs |
| `total_cost` instead of `unit_cost` | Quantity would become unexplained; product is `unit_cost × quantity` | Never for v1 |
| SQLModel/SQLite `job_runs` | Lock would not sit with telemetry or `pipeline_runs` | Never for DEV-53 |
| Compose scheduler / Celery Beat for nightly export | Nightly stays a host crontab example; DEV-55 worker is for the API producer only | If a later ticket owns scheduling |
| Daily `--target-date` on the clinic-supply CLI | Handoff forbids inventing pipeline CLI semantics | If a later ticket owns pipeline windows |
| XGBoost as the sales-forecast estimator | Extra dependency; RF is enough for 96 monthly rows | Later ticket asks to compare |
| Synthetic 75/25 US/UK rows to compute mix PSI | Would fabricate source data and make PSI circular | If a regional series is actually supplied |
| Numeric MAE/RMSE dollar cap for dashboard go/no-go | Briefing has no threshold; user chose the report card | User supplies a cutoff |
| Adding sklearn/xgboost to `services/api/pyproject.toml` | Would couple ML deps to FastAPI | Never for this feasibility script |
| Retuning the forest during the learning curve | Evaluation must score the frozen settings | If a later ticket owns a new search |
| Scoring 2024–2025 inside the fit diagnosis | The holdout has to stay unused | If a later ticket is explicitly a final test review |
| A shaded band on the learning curve | Each point is one chronological prefix, not a repeated sample | If a later design repeats each prefix |

## Still provisional

- Exact OAuth scope matrix and first write endpoint ordering (proposal §10).
- TS→Python migration window (proposal suggests ~two sprints after analytics endpoints ship).
- Real Resend inbox delivery depends on a local `RESEND_API_KEY` and a permitted from-address.
