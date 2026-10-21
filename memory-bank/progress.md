# Progress — Active iteration

## Current state

On `background-processes`. DEV-53 implemented locally: nightly CLI, `job_runner`, `job_runs.sql`, operator crontab example. Do not push, install cron, or apply warehouse DDL unless asked.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline.
- DEV-53 nightly export (code + unit tests).

## Validation results

- Focused pytest `tests/test_job_runner.py` + `tests/test_nightly_export.py` plus telemetry/pipeline/reporting: **48 passed**.
- Full `uv run pytest` in `services/api`: **165 passed**.
- CLI: `TARGET_DATE=2026-02-30` exits `2` with a failed log line (no job row).
- Unverified: live `job_runs.sql` apply, live unique-index two-process race, installed crontab.

## Blockers

None.

## Next steps

1. Wait for commit/push/PR or live SQL apply if asked.
2. Do not install host crontab unless authorized.

## Run commands (durable)

```bash
cd services/api && uv run pytest
./services/api/.venv/bin/python scripts/nightly_export.py
TARGET_DATE=YYYY-MM-DD ./services/api/.venv/bin/python scripts/nightly_export.py
```

Last updated: 2026-10-21
