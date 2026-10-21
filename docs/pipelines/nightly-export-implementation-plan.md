# DEV-53 implementation plan — nightly telemetry export

Ticket **#DEV-53**. Branch: `background-processes`. Contract: [`background-processes-context.md`](../../background-processes-context.md). Approved design choices (2026-10-21): `job_runs` in Supabase `reporting`; host crontab example; pipeline CLI unchanged.

**This file is the execution plan. Implementation starts only after explicit approval.** Approval of the design-choice plan is not approval to write code.

## Current committed state (inspected)

- Telemetry: `public.telemetry_events` via PostgREST; occurrence column is `timestamp`. Properties live in `tags` jsonb.
- Pipeline CLI: `python3 data/pipelines/pipeline.py` from repo root; re-execs `services/api/.venv` when prefect is missing. No date flag. Window is previous UTC month + 7-day lookback.
- `reporting.pipeline_runs` and KPI tables: [`docs/pipelines/reporting.sql`](reporting.sql). No `job_runs`. No Alembic. Warehouse SQL is applied manually.
- HTTP API does **not** schedule jobs. `POST /reporting/pipeline-runs` stays a manual JWT trigger.
- Compose is `ui` + `backend` only. `data/raw/` exists with READMEs and is not mounted.
- `scripts/` is the incident analyzer. Pytest lives under `services/api` (`uv run pytest`).
- Do not change `GET /telemetry/report` or `app/telemetry/analysis.py`. Leave `services/api/.coverage` untracked.

## What this ticket builds

One independent OS process that, for a UTC calendar day:

1. writes `data/raw/telemetry_YYYY-MM-DD.csv` if that final file is absent;
2. starts the existing pipeline as a subprocess exactly once;
3. records orchestration in `reporting.job_runs`;
4. skips quietly on overlap or an already-completed date.

CSV is a backup. The pipeline keeps reading `telemetry_events`.

## Files to add or change

| Path | Action |
|------|--------|
| `docs/pipelines/job_runs.sql` | New. `reporting.job_runs` + indexes + RLS. |
| `services/api/app/jobs/__init__.py` | New package. |
| `services/api/app/jobs/job_runner.py` | Status machine + PostgREST access (injectable). |
| `scripts/nightly_export.py` | CLI orchestrator. No inline status SQL. |
| `services/api/tests/test_job_runner.py` | State machine, dates, lock/idempotency fakes. |
| `services/api/tests/test_nightly_export.py` | CSV, subprocess, exit codes, retry-reuse. |
| `docs/pipelines/nightly-export.md` | Operator docs: cron, env, retry, evidence template. |
| `docs/pipelines/nightly_export.cron` | Example crontab (`0 2 * * *` UTC). Not installed. |
| `.gitignore` | Ignore `data/raw/telemetry_*.csv` (keep READMEs). |
| `data/raw/README.md` | Note: nightly CSVs are backups, not pipeline input. |
| `scripts/README.md` | Point at `nightly_export.py`. |
| `memory-bank/{context,spec,progress,decisions}.md` | Active iteration. |

Do **not** edit: `data/pipelines/pipeline.py` CLI/window, reporting HTTP routes, dashboard, Compose services, `app/main.py` lifespan, `GET /telemetry/report`.

## Schema: `reporting.job_runs`

Add [`docs/pipelines/job_runs.sql`](job_runs.sql) (do not rewrite `reporting.sql` tables). Apply the same way as reporting DDL: Supabase SQL editor / MCP when authorized. Tests never require live apply.

Columns (uuid PK like `pipeline_runs`):

- `id uuid primary key default gen_random_uuid()`
- `job_name text not null` (this process: `nightly_export`)
- `target_date date not null`
- `status text not null` with `check (status in ('pending','processing','completed','failed'))`
- `started_at timestamptz` null until processing
- `finished_at timestamptz` null until terminal
- `error_message text` null on success
- `created_at timestamptz not null default now()`

Indexes:

- btree `(job_name, target_date)` for lookups
- **partial unique** `(job_name) where status = 'processing'` — distributed lock
- **partial unique** `(job_name, target_date) where status = 'completed'` — one successful orchestration per date; failed rows remain retryable

Enable RLS. Comment `GRANT`s for `service_role` (same lesson as live pipeline smoke: PostgREST still needs `USAGE` on `reporting`). Do not apply to production unless asked.

PostgREST: `Accept-Profile` / `Content-Profile: reporting` on `/rest/v1/job_runs`. Telemetry export uses the **public** profile on `/rest/v1/telemetry_events` (no reporting profile).

Uniqueness conflict (HTTP 409 / PostgREST unique violation) is the overlap path, not a second lock.

## Service: `app.jobs.job_runner`

Injectable PostgREST helpers (same pattern as `pipelines.pipeline.set_run_log`). Default implementation uses `SUPABASE_URL` + service role key, loads `services/api/.env` like inventory/telemetry.

Required functions:

- `create_job_run(job_name, target_date) -> record` — insert `pending`
- `mark_processing(run_id, started_at)` — PATCH to `processing`; uniqueness conflict → overlap
- `mark_completed(run_id, finished_at)`
- `mark_failed(run_id, finished_at, error_message)` — sanitize: `{ExcType}: {short text}`, truncate, never URL/password/token/PHI/full traceback
- `has_processing_lock(job_name) -> bool` — any `processing` row for that job name
- `has_completed_for_date(job_name, target_date) -> bool`

Also: `JobOverlapError` for the 409 path. Only `pending → processing → completed|failed`. Refuse updates of a different `id`. If `mark_processing` loses the race after `create_job_run`, mark **that** pending row `failed` with a safe “overlap” message so it is not a pending zombie.

Do not import this module from FastAPI `lifespan` or routers.

## Script: `scripts/nightly_export.py`

Bootstrap (mirror pipeline CLI):

- Repo root = `Path(__file__).resolve().parents[1]`.
- Put `services/api` on `sys.path`. If `httpx` / app imports fail, re-exec `services/api/.venv/bin/python` when `sys.prefix` is not that venv.
- `cwd` for the child pipeline is the repo root.
- Load dotenv from `services/api/.env` without logging it.

Startup order (handoff):

1. UTC logging (`INFO` start/transitions/skip; `ERROR` failures). Every event includes timestamp, `job_name=nightly_export`, status, `target_date` when known, `job_run_id` when it exists.
2. Resolve `TARGET_DATE` (`YYYY-MM-DD`) or `datetime.now(timezone.utc).date() - timedelta(days=1)`. Inject/patch the clock in tests. Reject malformed/impossible dates **before** any insert (exit non-zero).
3. If `has_processing_lock`: log overlap, exit **0**, no new row.
4. If `has_completed_for_date`: log duplicate skip, exit **0**.
5. `create_job_run` → `mark_processing`.
6. Export CSV if final path missing (see below).
7. Subprocess once: `[sys.executable, str(repo_root / "data/pipelines/pipeline.py")]`, `shell=False`, copied env, timeout 900s. Non-zero, timeout, or missing file → job `failed`, parent exit non-zero. Do not pass a date flag.
8. `mark_completed`. Exit 0.

Caught failures after `processing` must `mark_failed` then re-raise/exit non-zero. Do not catch `BaseException` broadly. Document: `SIGKILL` / DB outage during the final PATCH can leave `processing`; no second lock; stale-run recovery is out of scope unless asked.

Exit codes: `0` success / duplicate / overlap; non-zero invalid date or failed eligible run.

## CSV contract

Path: `{repo_root}/data/raw/telemetry_YYYY-MM-DD.csv` (never the caller’s cwd).

- Query `telemetry_events` where `timestamp >= day_start` and `timestamp < next_day_start` (UTC, half-open).
- `select=id,timestamp,service,event_type,level,value,message,tags`
- `order=timestamp.asc,id.asc`
- Header always, including zero-event days.
- `tags` serialized with `json.dumps(..., sort_keys=True, default=str)`.
- Timestamps ISO 8601 UTC.
- If the **final** file exists, do not rewrite/append/truncate (retry after pipeline failure reuses it).
- Write `{filename}.tmp.{pid}` in the same directory, `os.replace` onto the final name only after a full successful write. On failure, delete only that temp file.

`.gitignore` `data/raw/telemetry_*.csv` so backups are not committed.

## Cron (documentation only)

[`docs/pipelines/nightly_export.cron`](nightly_export.cron):

```cron
CRON_TZ=UTC
0 2 * * * cd /ABS/REPO/ROOT && /ABS/REPO/ROOT/services/api/.venv/bin/python /ABS/REPO/ROOT/scripts/nightly_export.py >> /ABS/REPO/ROOT/data/raw/nightly_export.log 2>&1
```

Operator doc lists: expression + timezone (`02:00 UTC`), command, working directory, `SUPABASE_*` via `services/api/.env`, log and CSV locations, `TARGET_DATE=YYYY-MM-DD` manual run, how to inspect `job_runs` vs `pipeline_runs`, how to retry a failed date (leave CSV if present). Do **not** install crontab or change production.

## Tests (pytest, injectable fakes, no live Supabase)

[`services/api/tests/test_job_runner.py`](../../services/api/tests/test_job_runner.py)

- Default yesterday is UTC, not local; valid `TARGET_DATE`; malformed/impossible dates fail first.
- Month-end, year-end, leap-day (`2024-03-01` → `2024-02-29`; `2025-03-01` → `2025-02-28`).
- `pending → processing → completed` timestamps; failure → `failed` + `finished_at` + safe error.
- Illegal terminal → processing rejected.
- Completed lookup is `(job_name, target_date)`; processing lookup is job-name global.
- Fake unique index: second `mark_processing` raises overlap; pending zombie is failed.
- Completed date: orchestrator skip (tested with the script module).

[`services/api/tests/test_nightly_export.py`](../../services/api/tests/test_nightly_export.py)

- Window: event at `00:00Z` on target day included; `00:00Z` next day excluded.
- Header-only snapshot for zero events; stable column order; existing final file byte-identical after a skip/retry setup.
- Crash before replace leaves no final file; tmp cleaned.
- Unapproved columns absent (`password`, email, JWT).
- Successful child → completed; non-zero child → failed + non-zero parent; existing CSV reused and child invoked again.
- Command list uses `sys.executable`, repo-root script path, no `shell=True`.
- Logs include required fields and no `SUPABASE_SERVICE_ROLE_KEY`.

Concurrency: the fake store enforces one `processing` row across two sequential calls that simulate two connections. True two-OS-process / live unique-index proof is **optional later**, not a merge blocker.

Regression after job tests:

```bash
uv --directory services/api run pytest tests/test_job_runner.py tests/test_nightly_export.py
uv --directory services/api run pytest tests/test_telemetry_report.py tests/test_clinic_supply_pipeline.py tests/test_reporting.py
uv --directory services/api run pytest
```

Confirm `app/main.py` still has no scheduler import. Do not run website typecheck unless UI files change (they should not).

Manual scenarios (safe DB / `TARGET_DATE` only if authorized later): first run, duplicate skip, overlap, export failure, pipeline non-zero, retry reuse. Record commands; do not claim them passed unless run.

## Risks

| Risk | Handling |
|------|----------|
| Daily job vs monthly pipeline window | Documented; no new CLI flags |
| `job_runs` DDL not applied live | SQL file + fakes; CLI against missing schema fails `job_runs` writes and must `failed` or exit non-zero without claiming success |
| PostgREST 409 shape | Map status 409 and unique-violation body text in one helper; test the mapper |
| Script import path | `sys.path` + venv re-exec like `pipeline.py` |
| CSV in git | gitignore `telemetry_*.csv` |
| FastAPI accidentally scheduling | Do not import `app.jobs` from `main.py` |

## Acceptance criteria

- [ ] `reporting.job_runs` SQL with required fields, CHECK, UTC timestamps, lookup index, two partial unique indexes; distinct from `pipeline_runs`.
- [ ] `scripts/nightly_export.py` runnable via `services/api/.venv` python from documented paths.
- [ ] Default target = yesterday UTC; `TARGET_DATE=YYYY-MM-DD` works; bad dates fail before work.
- [ ] CSV is the UTC day’s approved telemetry backup; existing finals not overwritten; no partial final file.
- [ ] Pipeline invoked once per eligible run through `data/pipelines/pipeline.py` (no date flag).
- [ ] State `pending → processing → completed|failed`; `processing` is the only distributed lock; completed dates skipped; overlap exits 0.
- [ ] Crontab example is UTC `0 2 * * *` and is not installed.
- [ ] Focused pytest actually run; live unique-index / live warehouse noted as unverified unless authorized.
- [ ] Memory bank updated. No commit/push/PR unless asked.

## Stop condition

Do not implement until this plan is explicitly approved. Silence or design-choice approval is not implementation approval.
