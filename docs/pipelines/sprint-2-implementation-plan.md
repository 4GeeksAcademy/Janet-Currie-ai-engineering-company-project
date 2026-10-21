# Sprint 2 implementation plan (data-pipeline)

Build the resilient pipeline from the **committed** design. **Approved 2026-10-14.** Approval is not Sprint 3.

Branch: `data-pipeline` at `92618e8`. Design: [`data/pipelines/PIPELINE_DESIGN.md`](../../data/pipelines/PIPELINE_DESIGN.md). Contract: [`pipeline-context.md`](../../memory-bank/archive/2026-10-21-data-pipeline/pipeline-context.md).

Uncommitted leftovers (preserve; do not mix into the Sprint 2 commit): telemetry archive, `services/api/.coverage`, unstaged `progress.md` / capture-plan / `implementation-memory/telemetry.md`.

## Current committed state (inspected)

- Sprint 1 design + inbound `unit_cost` are in git. No `pipeline.py`, no Prefect, no `/reporting` routes, no `reporting` SQL.
- HTTP surface is one FastAPI app (`services/api`). Telemetry persist/report uses injectable PostgREST + pytest fakes.
- Backend deps: `uv` in `services/api` (`pyproject.toml`, `requirements.txt`, `uv.lock`). Docker installs `requirements.txt` system-wide. `data/pipelines/` is **not** copied into the backend image yet.
- Pytest lives in `services/api/tests` (`uv run pytest`). Serialization audit requires `response_model` + a `JSON_ROUTES` row per JSON path.
- `GET /telemetry/report` / `app/telemetry/analysis.py` stay untouched.

## What Sprint 2 builds

Prefect 3 ETL in `data/pipelines/pipeline.py`, reporting DDL, three authenticated `/reporting` routes on the existing API, focused tests. No dashboard, no subflow refactor (Sprint 3).

## Proposed decisions (for approval)

### 1. Prefect install path (`uv`, not a second toolchain)

Add `prefect>=3` to `services/api/pyproject.toml` and `requirements.txt`, then `uv lock` / keep `uv.lock` in the Sprint 2 commit (this is a real dependency change). Docker picks it up from `requirements.txt`.

KPI math stays in `data/pipelines/`. The API imports that module (repo root already used for `scripts/` in `app/main.py`).

### 2. CLI `python data/pipelines/pipeline.py`

Assignment command from **repo root**. This repo’s Python deps live in `services/api/.venv`. Plan:

- `pipeline.py` `if __name__ == "__main__"` runs `monthly_clinic_supply_performance()`.
- If `prefect` is missing, re-exec `services/api/.venv/bin/python` when that venv exists (so the assignment command works after `uv sync` in `services/api`).
- Documented equivalent: `uv --directory services/api run python ../../data/pipelines/pipeline.py`.
- Copy `data/pipelines` into `services/Dockerfile` (alongside `scripts`) so Compose can run the same file.

Do **not** add a second root `package.json` / pipenv project.

### 3. Warehouse = same PostgREST as telemetry (not SQLModel/SQLite)

Source is already Supabase `telemetry_events`. Destination `reporting.*` is the same host:

- SQL: [`docs/pipelines/reporting.sql`](reporting.sql) (`create schema reporting` + KPI table + `pipeline_runs` as designed).
- Load/read via PostgREST (`/rest/v1/reporting_...` **or** schema-qualified `reporting.monthly_clinic_supply_performance` with `Content-Profile` / `Accept-Profile`). Prefer PostgREST `reporting` schema + `Prefer: resolution=merge-duplicates` upsert on `(clinic_id, month_start)`.
- Tests never call live Supabase: injectable extract, load, run-log, and KPI readers (same pattern as `set_inserter` / `set_loader`).

Do not put reporting tables on inventory SQLite. Do not apply DDL to production. If local Supabase apply fails, leave the SQL file and record that CLI against empty credentials completes with `events_extracted = 0` (safe substitute).

### 4. Flow / tasks (names from the design)

| Piece | Name | I/O |
| --- | --- | --- |
| Flow | `monthly_clinic_supply_performance(month_start: date \| None)` | returns run metadata dict |
| Task | `extract_clinic_supply_events(window_start, window_end)` | list of raw event dicts |
| Task | `transform_clinic_month_kpis(events, window)` | `{rows, events_extracted, events_quarantined}` |
| Task | `load_monthly_clinic_supply_performance(rows)` | upsert count |
| Optional | `emit_clinic_supply_pipeline_heartbeat(run_id)` | `return_state=True`; failure must not fail the flow |

Pure transform helpers (no I/O) live in `data/pipelines/pipeline.py` (or `data/pipelines/transform.py` imported by it) so tests call them without Prefect scheduling.

Month default: previous UTC calendar month. Window: `[month_start, next_month_start + 7 days)` as designed.

### 5. Retries, cache, optional failure

- **Extract and load** (external HTTP): `@task(retries=3, retry_delay_seconds=5)` — comment: PostgREST blips; 3×5s is enough for a monthly job without hammering.
- **Transform**: no HTTP retries. `@task(cache_key_fn=..., cache_expiration=timedelta(hours=1))`. Cache key inputs: `window_start`, `window_end`, sorted `eventId` list (or hash). Document in the task docstring: a valid result is reused for one hour if the same window and same event ids are seen.
- **Heartbeat**: invoked with `return_state=True`. Tests force a failure; flow still `Completed`. Record heartbeat failure in logs / run `error` only if core ETL failed; optional failure is logged, not a `failed` run.

### 6. Run log and overlap

- Insert `reporting.pipeline_runs` as `running` at start; update `finished_at`, `status`, counts, `error` at end.
- In-process `threading.Lock` plus reject if a `running` row exists → POST **409**.
- `error` text: exception class + short message; never `userId`, email, tokens, PHI.

### 7. Reporting API (existing FastAPI app)

| Path | Auth | Behaviour |
| --- | --- | --- |
| `GET /reporting/monthly-clinic-supply-performance` | JWT | Optional `month_start`; default latest row’s month; empty table → **200** `{ "month_start": null, "clinics": [] }`; bad date → 400 |
| `GET /reporting/pipeline-runs/latest` | JWT | 200 metadata; **404** if none |
| `POST /reporting/pipeline-runs` | JWT | Optional `{ "month_start" }`; sync `monthly_clinic_supply_performance`; 200 metadata; **409** if locked/running |

Files:

- `services/api/app/reporting/schemas.py` — `ClinicSupplyKpi`, `MonthlyClinicSupplyPerformanceResponse`, `PipelineRunResponse`, `PipelineRunRequest`
- `services/api/app/reporting/queries.py` — PostgREST reads only (no KPI formulas)
- `services/api/app/routers/reporting.py` — `APIRouter(prefix="/reporting", dependencies=[Depends(get_current_user)])`
- `app/main.py` — `include_router`

Add three `JSON_ROUTES` entries in `test_serialization_audit.py`. Do **not** duplicate transform logic in `services/`.

Credentials: env `SUPABASE_URL` + service role (same as telemetry). Prefect block `healthcore-supabase` is optional later; Sprint 2 reads env so pytest stays offline. Do not log the key.

### 8. Out of scope

- Subflows / `tests/pipelines/test_pipeline.py` (Sprint 3)
- Dashboard / `uis/web` reporting page
- Changing `GET /telemetry/report` or `analysis.py`
- Live production apply, push, PR
- Currency conversion, clinic slugs, department grain

## Files expected to change

| Path | Action |
| --- | --- |
| `data/pipelines/pipeline.py` | Create: flow, tasks, CLI, injectables, lock |
| `docs/pipelines/reporting.sql` | Create: `reporting` schema + both tables |
| `services/Dockerfile` | Copy `data/pipelines` |
| `services/api/pyproject.toml`, `requirements.txt`, `uv.lock` | Add `prefect>=3` |
| `services/api/app/main.py` | Include reporting router; sys.path already has repo patterns |
| `services/api/app/reporting/schemas.py` | Create |
| `services/api/app/reporting/queries.py` | Create |
| `services/api/app/routers/reporting.py` | Create |
| `services/api/tests/test_clinic_supply_pipeline.py` | Create: transform, quarantine, idempotency, heartbeat `return_state` |
| `services/api/tests/test_reporting.py` | Create: auth, empty GET, 400, 404, 409, 200 shape |
| `services/api/tests/test_serialization_audit.py` | Three JSON_ROUTES |
| `memory-bank/{context,spec,progress,decisions}.md` | Sprint 2 status |

## Implementation steps (after approval)

1. Add Prefect via `uv` and lockfile.
2. Write `reporting.sql` and `pipeline.py` (pure transform + tasks + flow + CLI + injectables).
3. Wire reporting schemas/queries/router; mount on `app`.
4. Copy `data/pipelines` in the backend Dockerfile.
5. Tests as below. Do not hit production.
6. Update memory bank. Commit: `feat: implement resilient business performance pipeline`.
7. Stop. Do not write the Sprint 3 plan until asked.

## Tests and validation

Narrowest first:

```bash
cd services/api && uv run pytest tests/test_clinic_supply_pipeline.py tests/test_reporting.py tests/test_serialization_audit.py tests/test_telemetry_report.py
```

Then `uv run pytest` if focused pass.

| Case | Assert |
| --- | --- |
| Empty events | `completed`, 0 rows, `events_extracted=0` |
| Four KPI types | Cost = `unit_cost × quantity`; consumption is **count** not qty sum; stockout/expiry counts |
| Duplicate `eventId` | One contribution |
| Bad `unit_cost` / clinic / country | Quarantined; run still completes |
| Month boundary + late event in +7d window | Lands in UTC month of `timestamp` |
| US vs UK | Separate rows; USD vs GBP; no combined total |
| Idempotency | Same window twice → identical KPI rows, no duplicate keys |
| Heartbeat failure | `return_state=True`; flow completed |
| GET reporting | 401 without token; 200 empty; 400 bad `month_start`; 200 populated |
| GET latest | 404 then 200 after a run |
| POST | 200; second overlapping POST 409 |
| Telemetry report | Existing tests still pass |

CLI: run `python data/pipelines/pipeline.py` with the API venv and **no** live Supabase (or empty fake). Expect a completed run with zero extracted events if credentials are missing — report that as the safe substitute; do not claim a production warehouse load.

Typecheck: not required for Python-only API work beyond pytest. Do not run website typecheck unless UI files change (they should not).

## Risks

| Risk | Handling |
| --- | --- |
| Live `reporting` schema missing | SQL file + in-memory tests; CLI empty-extract substitute |
| Prefect heavy in Docker image | Acceptable; required by assignment |
| Import path `data.pipelines` vs `pipelines` | Package via repo root on `sys.path` (`data/pipelines/__init__.py` empty) |
| PostgREST schema `reporting` | Confirm header/profile in impl; tests use fakes so URL shape can stay in one helper |
| `uv.lock` leftover previously | Include lockfile this time because Prefect is a real dep |

## Sprint 2 acceptance criteria

- [ ] `data/pipelines/pipeline.py` has the named flow/tasks, retries, 1h transform cache, optional heartbeat, run metadata, idempotent load, CLI.
- [ ] `docs/pipelines/reporting.sql` matches the design tables.
- [ ] Three JWT `/reporting` endpoints; no ETL copy in `services/`.
- [ ] Technical telemetry tests unchanged in behaviour.
- [ ] Focused tests actually run; limitations recorded.
- [ ] Commit `feat: implement resilient business performance pipeline` before Sprint 3 planning.

## Stop condition

This file is the plan. Implementation starts only after explicit approval.
