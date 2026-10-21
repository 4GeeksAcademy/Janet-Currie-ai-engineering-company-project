# Sprint 3 implementation plan (data-pipeline)

Refactor the committed Sprint 2 pipeline into subflows, add isolated unit tests, and ship the board dashboard. **Approved 2026-10-19.** Approval of Sprint 2 is not approval of this sprint.

Branch: `data-pipeline` at `d4df11c`. Design: [`data/pipelines/PIPELINE_DESIGN.md`](../../data/pipelines/PIPELINE_DESIGN.md). Contract: [`pipeline-context.md`](../../memory-bank/archive/2026-10-21-data-pipeline/pipeline-context.md).

Uncommitted leftovers (preserve; do not mix into the Sprint 3 commit): telemetry archive (`Telemetry-Context.md` delete + `memory-bank/archive/2026-10-14-telemetry/`), `docs/telemetry/capture-implementation-plan.md`, `memory-bank/implementation-memory/telemetry.md`, `services/api/.coverage`.

## Current committed state (inspected)

- Sprint 2 is on `d4df11c` (`feat: implement resilient business performance pipeline`), in sync with `origin/data-pipeline`.
- ETL: `data/pipelines/pipeline.py` — pure `transform_clinic_month_kpis`, `@task` extract/transform/load (retries 3×5s on extract/load; 1h transform cache), optional heartbeat, in-process lock, `execute_monthly_clinic_supply_performance` for HTTP/CLI/tests, `@flow monthly_clinic_supply_performance` wrapper. **No subflows yet.**
- CLI `python3 data/pipelines/pipeline.py` re-execs `services/api/.venv` and calls **`execute_…`**, not the `@flow`, so it does not start Prefect’s ephemeral server.
- HTTP (JWT, existing FastAPI app): `GET /reporting/monthly-clinic-supply-performance`, `GET /reporting/pipeline-runs/latest`, `POST /reporting/pipeline-runs` (409 if running). Empty KPI table → 200 `{ "month_start": null, "clinics": [] }`.
- Destination table is already `reporting.monthly_clinic_supply_performance` (not `clinic_month_kpis`). Live DDL still not applied.
- Transform coverage lives in `services/api/tests/test_clinic_supply_pipeline.py`. There is **no** `tests/pipelines/test_pipeline.py`.
- Staff UI is `uis/web` (port 3001). `uis/backoffice/` does not exist as an app. Inventory already uses `/backoffice/inventory/...` inside `uis/web`, with `BackofficeShell`, `AuthGuard`, `apiFetch`, `useAsyncResource`, `ErrorBanner`, and Jest (`inventoryViews.test.tsx`).
- Calling `@flow` from pytest hung (~4 min, aborted). Sprint 3 must not reintroduce that.

## What Sprint 3 builds

1. Three independently executable `@flow` subflows (extract, transform, load) with the main flow as coordinator.
2. Isolated unit tests at `tests/pipelines/test_pipeline.py`.
3. Preserved CLI (`execute_…` entry point).
4. Board dashboard in `uis/web` at `/backoffice/reporting/monthly-clinic-supply-performance`.
5. Only the design’s already-prioritized optional extras: heartbeat as a subflow (`return_state=True`) and latest-run status on the dashboard. No advisory lock, no POST-from-UI, no FX, no clinic slugs.

## Proposed decisions (for approval)

### 1. Subflows wrap existing tasks; HTTP/CLI stay on `execute_…`

| Piece | Name | Inputs | Output |
| --- | --- | --- | --- |
| Main flow | `monthly_clinic_supply_performance` | `month_start: date \| None` | run metadata dict |
| Subflow | `extract_clinic_supply_events_flow` | `window_start`, `window_end` | list of event dicts |
| Subflow | `transform_clinic_month_kpis_flow` | `events`, `window` | `{rows, events_extracted, events_quarantined}` |
| Subflow | `load_monthly_clinic_supply_performance_flow` | `rows` | upsert count |
| Optional subflow | `emit_clinic_supply_pipeline_heartbeat_flow` | `run_id` | invoked with `return_state=True` |

Each subflow calls the existing `@task` (retries/cache stay on the tasks). No globals for I/O. KPI math stays in `transform_clinic_month_kpis`.

**Coordinator split (required so pytest/API do not hang):**

- `execute_monthly_clinic_supply_performance` remains the production runner for CLI, `POST /reporting/pipeline-runs`, and API tests. It keeps calling `task.fn()` (and the optional heartbeat in a try/except).
- The `@flow` main coordinator invokes the three ETL subflows (plus heartbeat `return_state=True`) with the same explicit contracts. It is for Prefect deploy / rubric topology only.
- Do **not** call any `@flow` from FastAPI, pytest, or the CLI `__main__` block.

**How we prove the topology without the ephemeral server:** a test inspects that `monthly_clinic_supply_performance` is a Prefect flow whose callable source references the three named subflows. Independently executable means each subflow is a `@flow` with explicit args/return; tests exercise the inner functions (`transform_clinic_month_kpis`, `task.fn()`), not `flow()`.

CLI: keep `if __name__ == "__main__": execute_monthly_clinic_supply_performance()` and the venv re-exec. Assignment command from repo root still works.

### 2. Unit tests at repo-root `tests/pipelines/test_pipeline.py`

Assignment path is `tests/pipelines/test_pipeline.py` with no database/API. This repo’s pytest lives under `services/api`. Plan:

- Create `tests/pipelines/test_pipeline.py` plus a tiny `tests/pipelines/conftest.py` that only puts `data/` on `sys.path`.
- Tests import `pipelines.pipeline` and call **`transform_clinic_month_kpis` only** (in-memory telemetry-shaped fixtures).
- Keep Sprint 2 files `services/api/tests/test_clinic_supply_pipeline.py` and `test_reporting.py` (do not delete or weaken them).

At least three isolated transform tests; cover all four KPIs; include:

| Test | Assert |
| --- | --- |
| Empty input | `rows == []`, `events_extracted == 0` |
| Four KPIs + hand-calculated cost | inbound `2 × 4.5 + 1 × 10 = 19.0`; consumption is **count** (two outbound with qty 50 and 7 → 2, not 57); stockout 1; expiry 3 |
| Duplicate `eventId` | one contribution |
| Bad `unit_cost` / missing cost / bad clinic / bad country | quarantined; valid rows still emitted |
| Month boundary / late event | UTC month of `timestamp`; event in +7d lookback still assigns to its own month |
| US vs UK | two rows; `USD` vs `GBP`; no combined total field |
| Subflow wiring | main flow source references the three subflow names (no `flow()` call) |

**Commands:**

```bash
uv --directory services/api run pytest ../../tests/pipelines/test_pipeline.py
cd services/api && uv run pytest tests/test_clinic_supply_pipeline.py tests/test_reporting.py tests/test_serialization_audit.py tests/test_telemetry_report.py
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
```

Documented assignment equivalent (same venv): `services/api/.venv/bin/python -m pytest tests/pipelines/test_pipeline.py` from repo root.

### 3. Dashboard in `uis/web`, not a second app

Syllabus `uis/backoffice/` is this repo’s **`uis/web`** with `/backoffice/...` URLs (same as inventory; Sprint 1 design already chose this).

| Path | Role |
| --- | --- |
| `uis/web/src/lib/reporting.ts` | Typed `fetchMonthlyClinicSupplyPerformance` / `fetchLatestPipelineRun` via `apiFetch` + `readJson`. **No direct DB.** |
| `uis/web/src/components/reporting/MonthlyClinicSupplyReport.tsx` | Board page: loading / empty / error / populated |
| `uis/web/src/app/(protected)/backoffice/reporting/monthly-clinic-supply-performance/page.tsx` | Protected route (existing `AuthGuard` + `BackofficeShell`) |
| `uis/web/src/components/BackofficeShell.tsx` | Nav item **Clinic supply report** |
| `uis/web/src/components/reporting/__tests__/MonthlyClinicSupplyReport.test.tsx` | Jest: loading, empty, error+retry, populated US/UK, no cross-currency total |
| `uis/web/src/lib/__tests__/reporting.test.ts` | Helper builds the KPI URL (`month_start` query when set) |

**UI contract (Dr. Okonkwo / Claire, not engineers):**

- Title: **Monthly Clinic Supply Performance**.
- Reporting month from `month_start` (e.g. `July 2026`). Empty API → “No clinic-month supply performance has been computed yet.”
- Exact labels: **Supply Cost per Clinic**, **Supply Consumption Volume**, **Critical Stockout Frequency**, **Expiry Risk Count**.
- Two country sections: **United States (USD)** and **United Kingdom (GBP)**. Never a combined total row or summed cost.
- Clinic ids stay `"1"`–`"12"` (display “Clinic 1”). Currency shown per row (`USD` / `GBP` or `$` / `£` within that section only).
- Latest-run line from `GET /reporting/pipeline-runs/latest` (404 → “No pipeline run recorded yet”, not a page error). Answers design §11 traceability. No “Run pipeline” button (operators already have POST).
- Loading copy: “Loading monthly clinic supply performance…”. Errors: existing `ErrorBanner` + retry (`toUserMessage`, no raw `detail`).
- Optional month `<input type="month">` that refetches `?month_start=YYYY-MM-01`. Default is the API’s latest month.

Do not add `uis/backoffice/` as an app. Do not query Supabase from the browser.

### 4. Optional enhancements (only those already in the design)

| Design question | Sprint 3 action |
| --- | --- |
| Zero activity vs capture failure | Keep Sprint 2 heartbeat; wrap it as `emit_clinic_supply_pipeline_heartbeat_flow` with `return_state=True` on the main flow |
| Traceability | Show latest `pipeline_runs` metadata on the dashboard |
| Concurrent runs | Keep in-process lock + 409. **No** Postgres advisory lock (still one API process locally) |
| Idempotency-key header | Out of scope (ingest unchanged) |

Update [`data/pipelines/PIPELINE_DESIGN.md`](../../data/pipelines/PIPELINE_DESIGN.md) §9–§11 to record that subflows exist, CLI still uses `execute_…`, and which optional items shipped. Do not change KPI math, table, or HTTP paths.

### 5. Out of scope

- Changing `GET /telemetry/report` or `app/telemetry/analysis.py`
- Live production Supabase apply, push, PR
- Currency conversion, clinic slugs, department grain, PHI
- New backend / `services/reporting` process
- Mixing leftover telemetry archive / `.coverage` into this commit
- Calling `@flow()` from tests or FastAPI

## Files expected to change

| Path | Action |
| --- | --- |
| `data/pipelines/pipeline.py` | Add three ETL `@flow` subflows + heartbeat subflow; main flow calls them; keep `execute_…` + CLI |
| `data/pipelines/PIPELINE_DESIGN.md` | Note subflows, CLI runner, shipped optional extras |
| `tests/pipelines/conftest.py` | Create: `sys.path` only |
| `tests/pipelines/test_pipeline.py` | Create: isolated transform + wiring tests |
| `uis/web/src/lib/reporting.ts` | Create |
| `uis/web/src/components/reporting/MonthlyClinicSupplyReport.tsx` | Create |
| `uis/web/src/app/(protected)/backoffice/reporting/monthly-clinic-supply-performance/page.tsx` | Create |
| `uis/web/src/components/BackofficeShell.tsx` | Nav link |
| `uis/web/src/components/reporting/__tests__/MonthlyClinicSupplyReport.test.tsx` | Create |
| `uis/web/src/lib/__tests__/reporting.test.ts` | Create |
| `memory-bank/{context,spec,progress,decisions}.md` | Sprint 3 status |
| `memory-bank/implementation-memory/clinic-supply-pipeline.md` + `index.md` | Durable notes after validation |

Unchanged unless a bug blocks the sprint: reporting SQL, FastAPI routes, `JSON_ROUTES`.

## Implementation steps (after approval)

1. Add subflows and retarget the main `@flow`; leave `execute_…` and CLI as the runtime path.
2. Add `tests/pipelines/test_pipeline.py` (no DB/HTTP).
3. Add reporting fetch helper + dashboard + nav + Jest.
4. Point `PIPELINE_DESIGN.md` at the new topology.
5. Validate as below. Do not hit production.
6. Update memory bank. Commit: `feat: refactor business performance pipeline into subflows, add unit tests, and add reporting dashboard`.
7. Stop. Do not push or open a PR unless asked.

## Tests and validation

Narrowest first:

```bash
uv --directory services/api run pytest ../../tests/pipelines/test_pipeline.py
cd services/api && uv run pytest tests/test_clinic_supply_pipeline.py tests/test_reporting.py tests/test_serialization_audit.py tests/test_telemetry_report.py
npm test -w uis/web -- --coverage=false --testPathPatterns="reporting|MonthlyClinicSupplyReport"
npm run typecheck -w uis/web
python3 data/pipelines/pipeline.py
```

Then full `cd services/api && uv run pytest` if focused Python passes.

Before commit, run [`skills/pre-delivery-verification`](../../skills/pre-delivery-verification/SKILL.md) (UI changed): typecheck, protected paths untouched, progress updated.

Dashboard smoke: Jest covers loading / populated / empty / error. If staff UI + API are already running locally, exercise the route in the browser (login → nav → report). If they are not, record Jest as the verified substitute and do not claim a headed smoke passed.

CLI: same safe substitute as Sprint 2 — completed run with `events_extracted=0` when `SUPABASE_URL` is unset. Do not claim a live warehouse load. Do not apply `reporting.sql` to production.

## Risks

| Risk | Handling |
| --- | --- |
| `@flow()` in pytest hangs | Never call flows in tests; inspect names + test `transform_clinic_month_kpis` / `execute_…` |
| Duplicate transform tests | Root `tests/pipelines/` is the assignment artifact; keep Sprint 2 API tests |
| Empty warehouse / no DDL | Dashboard empty state is a real 200, not an error |
| Cross-currency total by accident | Two sections; Jest asserts no combined cost |
| Leftover telemetry files | Leave unstaged |

## Sprint 3 acceptance criteria

- [ ] Main flow coordinates at least three named HealthCore `@flow` subflows with explicit I/O; heartbeat still `return_state=True`.
- [ ] `tests/pipelines/test_pipeline.py` exists; isolated transform tests cover all four KPIs, a hand-calculated cost, malformed input, empty, duplicates, month/currency boundaries; no DB/API.
- [ ] `python3 data/pipelines/pipeline.py` still completes via `execute_…`.
- [ ] JWT dashboard at `/backoffice/reporting/monthly-clinic-supply-performance` fetches `GET /reporting/monthly-clinic-supply-performance`, shows the four business labels and reporting month, separates USD and GBP, contains no PHI.
- [ ] Focused pytest, Jest, typecheck actually run; limitations recorded.
- [ ] Commit message exactly: `feat: refactor business performance pipeline into subflows, add unit tests, and add reporting dashboard`.
- [ ] No push/PR unless asked.

## Stop condition

This file is the plan. Implementation starts only after explicit approval.
