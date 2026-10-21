# Progress — Active iteration

## Current state

On `background-processes`. DEV-53 design choices recorded. Detailed execution plan: [`docs/pipelines/nightly-export-implementation-plan.md`](../docs/pipelines/nightly-export-implementation-plan.md). **Do not implement until that plan is explicitly approved.** Do not push or open a PR unless asked.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline.
- DEV-53 design: `job_runs` in Supabase `reporting`; host crontab example; pipeline CLI/window unchanged; `02:00 UTC` documented default.

## Validation results

None for DEV-53 yet (plan only). Docs-only: execution plan and memory-bank pointers written.

## Blockers

Waiting for explicit approval of the execution plan.

## Next steps

1. Wait for approval of [`docs/pipelines/nightly-export-implementation-plan.md`](../docs/pipelines/nightly-export-implementation-plan.md).
2. Do not write job SQL, `job_runner`, or `nightly_export.py` until then.

## Run commands (durable)

```bash
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
```

Last updated: 2026-10-21
