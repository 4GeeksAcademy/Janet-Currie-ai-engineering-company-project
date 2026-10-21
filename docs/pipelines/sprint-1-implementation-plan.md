# Sprint 1 implementation plan (data-pipeline)

Design-only sprint. **Approved 2026-10-14.** Approval of this plan is not approval of Sprint 2 or Sprint 3.

Branch: `data-pipeline`. Contract: [`pipeline-context.md`](../../pipeline-context.md). Authority: HealthCore pipeline context, then the three 4Geeks sprint READMEs. Existing monorepo conventions win where those sources leave a choice open.

## Current committed state (inspected)

Latest commit on this branch: `aa7b183` (telemetry report). Uncommitted work already on the tree (preserve; do not mix into the Sprint 1 design commit unless asked):

- telemetry archive under `memory-bank/archive/2026-10-14-telemetry/`
- filled `pipeline-context.md`
- leftover `services/api/.coverage` (never commit)

No Prefect, no `data/pipelines/pipeline.py`, no reporting schema, no `services/reporting/` package. `data/pipelines/` has README files only.

## Repo facts that shape the design

| Area | What exists |
|------|-------------|
| HTTP API | Single FastAPI app at `services/api` (`app/main.py`). Telemetry lives in `app/telemetry/` + `app/routers/telemetry.py`, not a separate `services/telemetry/` process. |
| Source table | `public.telemetry_events` via PostgREST (`docs/telemetry/telemetry_events.sql`). Columns: `id`, `timestamp`, `service`, `event_type`, `level`, `value`, `message`, `tags` jsonb. Envelope fields including `eventId` are **inside `tags`**, not first-class columns. Live DDL may still need manual apply. |
| Event properties | `inbound_order_created` allowlist: `clinic_id`, `country`, `product_id`, `product_category`, `quantity`. **No `unit_cost` or `total_cost`.** Inventory `MedicalSupply` has no price column. Delivery form does not collect cost. |
| `clinic_id` | Integer `1`–`12` in inventory + telemetry (`CLINIC_IDS`). Syllabus JSON example `"austin-north"` is **not** in this repo. |
| Technical report | `GET /telemetry/report` — daily volume/errors/latency/auth. Not clinic-month, not the four business KPIs. Do not change `analysis.py` or that contract. |
| Staff UI | `uis/web` on port 3001. `uis/backoffice/` does not exist as an app. Inventory URLs already use `/backoffice/inventory/...` inside `uis/web`. |
| Auth | Inventory/incidents/suppliers routers use `Depends(get_current_user)`. Telemetry ingest is public. |
| Persistence | Inventory: SQLModel + `DATABASE_URL` (SQLite locally, Postgres in prod). Telemetry: Supabase PostgREST only. No Alembic. Schema changes are SQL files (same pattern as `telemetry_events.sql`). |
| Tests | API: `cd services/api && uv run pytest`. Staff: `npm test -w uis/web`. No `tests/pipelines/` yet. |
| Dependencies | `uv` + `pyproject.toml` / `requirements.txt` in `services/api`. Prefect is **not** installed (Sprint 2). |

## Sprint 1 deliverable (after approval)

Create and commit:

```text
data/pipelines/PIPELINE_DESIGN.md
```

That document must cover all 12 required design sections in `pipeline-context.md` (current state/gap through testing strategy).

**Also after approval (smallest additive capture extension, not a new event type):**

| File | Change |
|------|--------|
| `docs/telemetry/event-schemas.json` | Add required `unit_cost` (`number`, `> 0`) to `inbound_order_created.properties`. |
| `docs/telemetry/telemetry-plan.md` | Document `unit_cost` on inbound; computation note. |
| `uis/web/src/lib/telemetry.ts` | Add `unit_cost` to the inbound allowlist; pass it through `inventoryProperties` when provided. |
| `uis/web/src/components/inventory/SupplyDeliveryForm.tsx` | Collect a positive `unit_cost` and include it on `inbound_order_created` only. |
| `uis/web/src/lib/__tests__/telemetry.test.ts` and inventory view tests | Allowlist keeps `unit_cost`; strips unknown keys; form still does not send PII. |

Keep this off the technical report path: no edits to `app/telemetry/analysis.py` or `GET /telemetry/report`.

### Not in Sprint 1

- Prefect, `pipeline.py`, retries/cache/subflows
- `reporting` schema, `pipeline_runs` table, migrations applied
- `services/reporting/` or any `/reporting/*` router
- Dashboard
- Currency conversion, department-grain tables, patient data
- Push / PR

## Proposed design decisions (for approval)

These will be written into `PIPELINE_DESIGN.md` if you approve them. They do not change the four KPIs, monthly clinic grain, destination table DDL, three endpoints, or privacy boundary.

### 1. Cost formula (required — field is missing)

`inbound_order_created` has quantity but no cost. Inventory has no unit price.

- Add **`unit_cost`** (not `total_cost`) so quantity stays explanatory.
- Per event: `event_cost = unit_cost × quantity`.
- KPI: `total_supply_cost = sum(event_cost)` for `inbound_order_created` in that clinic-month.
- Currency is **not** on the event; it is derived from `country` (`US` → `USD`, `UK` → `GBP`).
- Events missing, non-numeric, or `unit_cost <= 0` are skipped for the cost KPI and counted in the run log as quarantined; they do not fail the run.

### 2. `clinic_id` text vs integers

Destination column is `text`. This app already uses integer clinics `1`–`12`. Do **not** invent slugs such as `austin-north`.

- Store `clinic_id` as the decimal string of the integer (`"1"` … `"12"`).
- Drop events whose `clinic_id` is missing or outside 1–12.

### 3. Reporting HTTP module vs a second service

Handoff path `services/reporting/` maps onto this repo as:

- `services/api/app/reporting/` (load/query helpers, Pydantic models)
- `services/api/app/routers/reporting.py` mounted at `/reporting`
- ETL remains in `data/pipelines/`; routers call pipeline functions/flows and do not reimplement KPI math

One FastAPI process, same JWT `get_current_user` as inventory. Matches “APIs live under `services/`” and “do not create a new backend.”

### 4. Manual run semantics

`POST /reporting/pipeline-runs` runs the flow **synchronously** in the request (same process as other FastAPI work). If a run is already `running`, return **409**. No background worker in v1.

### 5. Schedule

Prefect deployment: `0 6 1 * *` (06:00 UTC on calendar day 1). Operators use POST if the 1st falls on a weekend and the pack must go out on the next working day. Exact timezone stays UTC because `month_start` is UTC.

### 6. Extraction window and late events

Default run for month `M`: extract events with `timestamp` in `[M, M+1 month + 7 days)` so late arrivals in the first week of the next month still land in month `M`. Recompute and upsert every affected `(clinic_id, month_start)`. Idempotency: drop duplicate `tags.eventId` before aggregation; upsert on `(clinic_id, month_start)`.

### 7. Prefect names (Sprint 2, designed now)

| Kind | Name |
|------|------|
| Main flow | `monthly_clinic_supply_performance` |
| Extract task | `extract_clinic_supply_events` |
| Transform task | `transform_clinic_month_kpis` |
| Load task | `load_monthly_clinic_supply_performance` |
| Optional (non-critical) | `emit_clinic_supply_pipeline_heartbeat` via `return_state=True` |
| Block | `healthcore-supabase` (URL + service role; never log the key) |

CLI: `python data/pipelines/pipeline.py` from repo root (Sprint 2). Prefect `>=3` added with `uv` in `services/api` **or** a root/pipeline extra — Sprint 2 plan will pick the smallest install path after this design lands. Do not install Prefect in Sprint 1.

### 8. Control table (designed now, created in Sprint 2)

`reporting.pipeline_runs` with at least:

| Field | Type | Why |
|-------|------|-----|
| `run_id` | uuid PK | Correlate logs and API `latest` |
| `started_at` | timestamptz | Duration and “is it running” |
| `finished_at` | timestamptz null | Distinguishes in-flight vs done |
| `status` | text (`running` \| `completed` \| `failed`) | Prefect-aligned |
| `records_processed` | integer | Output row count (clinic-months upserted) |
| `error` | text null | Captured failure, no PHI |
| `window_start` / `window_end` | timestamptz | Source window actually read |
| `events_extracted` | integer | Input volume vs silence |
| `events_quarantined` | integer | Malformed/skipped vs zero activity |

Zero extracted events + `completed` means genuine inactivity. Extract/load HTTP failure → `failed` with `error` set.

### 9. Sprint 3 dashboard location

Staff app is `uis/web`, not a separate `uis/backoffice` package. Future page (not built now): `uis/web/src/app/(protected)/backoffice/reporting/monthly-clinic-supply-performance/page.tsx`, URL `/backoffice/reporting/monthly-clinic-supply-performance`. Fetches `GET /reporting/monthly-clinic-supply-performance` only.

### 10. Overlapping runs

Sprint 2: in-process lock + `running` row. Sprint 3 optional: DB unique partial index / advisory lock if concurrent API workers appear. Design document will split required vs optional resilience this way.

## `PIPELINE_DESIGN.md` outline (what will be written)

1. Current telemetry vs business gap (`GET /telemetry/report` vs monthly clinic pack).
2. One-sentence purpose (Okonkwo/Claire, four KPIs, four source events).
3. Extraction contract (`telemetry_events` read-only; four `event_type`s; `tags` payload; window; filters).
4. Mermaid extract → transform → load with real table names.
5. Transform contract (UTC month, counts vs cost sum, currency, quarantine, dedupe, late events).
6. Exact `reporting.monthly_clinic_supply_performance` DDL and three endpoints with the JSON shape from the handoff (clinic ids as `"1"`…`"12"`).
7. Idempotency (`eventId`, upsert, rerun, late recompute, 409 overlap).
8. `pipeline_runs` fields/types/rationale; heartbeat vs silence.
9. Prefect mapping (names above), states, block, schedule, CLI.
10. Application integration: each endpoint → `data/pipelines` function; no ETL in `services/`.
11. Resilience Q&A with Sprint 2 vs Sprint 3 split.
12. Test plan pointing at later `tests/pipelines/test_pipeline.py` and reporting API tests.

## Implementation steps (after approval only)

1. Write `data/pipelines/PIPELINE_DESIGN.md` covering every required section.
2. Apply the additive `unit_cost` schema/allowlist/form/tests listed above.
3. Update active `memory-bank/` (progress, spec checkboxes, any adopted decisions).
4. Validate.
5. Local commit with message `feat: add business performance pipeline design document`.
6. Stop. Do not write the Sprint 2 plan until you ask to start Sprint 2.

## Tests and validation (Sprint 1)

- Docs: `PIPELINE_DESIGN.md` exists and covers the 12 sections, five+ run-log fields, named flow + three tasks, three endpoints, no Prefect/reporting code added.
- If `unit_cost` is approved: `npm test -w uis/web -- src/lib/__tests__/telemetry.test.ts` and focused inventory form tests; `npm run typecheck -w uis/web`.
- No pytest suite change expected unless a test asserts the inbound allowlist without `unit_cost`.
- Do not run Prefect or hit production Supabase.

## Risks and assumptions

| Risk / assumption | Handling |
|-------------------|----------|
| Live `telemetry_events` table may not exist yet | Design still targets that SQL; Sprint 2 validation may use a fake loader (same pattern as telemetry tests). |
| No supply price in inventory | Cost comes from the inbound form `unit_cost`, not a catalogue join. |
| Syllabus clinic slugs vs numeric ids | Use `"1"`–`"12"`; document the example JSON as illustrative. |
| `services/reporting/` vs `services/api` | One app, `app/reporting` package; stated above for approval. |
| Dirty working tree | Sprint 1 commit stays scoped to design + approved `unit_cost` capture; archive/coverage stay out unless you ask. |
| `value` column currently stores quantity for inbound | Pipeline reads `tags.unit_cost` and `tags.quantity`, not `telemetry_events.value`, so technical report stays untouched. |

## Sprint 1 acceptance criteria

- [ ] `data/pipelines/PIPELINE_DESIGN.md` is HealthCore-specific and complete vs `pipeline-context.md`.
- [ ] Cost-field gap is closed in the design (and in capture schema/form if this plan is approved as written).
- [ ] No Prefect pipeline, reporting service, or dashboard built.
- [ ] Focused tests for `unit_cost` allowlist/form actually run if that change is included.
- [ ] Sprint committed with the assignment message before Sprint 2 planning.

## Stop condition

This file is the plan. Implementation starts only after explicit approval (including any edits you request to the decisions above).
