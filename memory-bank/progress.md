# Progress — Active iteration

## Current state

Data-pipeline iteration archived under [`archive/2026-10-21-data-pipeline/`](archive/2026-10-21-data-pipeline/). Durable notes: [`implementation-memory/clinic-supply-pipeline.md`](implementation-memory/clinic-supply-pipeline.md). No active pipeline work. Do not push or open a PR unless asked.

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API, inventory backoffice UI, Docker Compose, Web Vitals, serialization, caching, telemetry, clinic-supply pipeline.

## Validation results

Pipeline live smoke (2026-10-21): CLI completed with `events_extracted=0`; dashboard showed that run. Populated US/UK KPI rows were not shown (empty `telemetry_events`).

## Blockers

None.

## Next steps

1. Wait for the next asked task.

## Run commands (durable)

```bash
cd services/api && uv run pytest
python3 data/pipelines/pipeline.py
```

Last updated: 2026-10-21
