# Progress — Active iteration

## Current state

Web Vitals audit complete for this iteration. Protocol and baseline: [`AUDIT.md`](../AUDIT.md). Corrections and before/after: [`REPORT.md`](../REPORT.md).

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188), inventory backoffice UI, Docker Compose dev stack (`c96f167`).
- Web Vitals (2026-09-23): baseline + targeted fixes + `LangToggle` / `useAsyncResource` refactor. Website mobile Performance 94 → 96; staff Accessibility 95 → 100.

## Validation results

HCR-0188 (2026-09-18): 16 inventory pytest passed; 96 full pytest. Inventory UI: 34 Jest, typecheck, live smoke (`afb1bed`). infra-40: Compose verified (`c96f167`).

Web Vitals (2026-09-23):

- `npm run typecheck` pass
- `npm run lint -w uis/website` and `npm run lint -w uis/web` pass
- `npm test -w uis/web` 37 passed (`useAsyncResource` 100% coverage)
- both `next build`s pass
- Lighthouse after matrix in `audit/after/`
- Browser smoke of `/` EN/ES; authenticated Lighthouse of `/operations`

## Blockers

None.

## Next steps

Archive this phase when wrap-up is requested.

## Run commands (durable)

```bash
npm run build -w uis/website && npm run start -w uis/website
npm run build -w uis/web && npm run start -w uis/web
cd services/api && uv run uvicorn app.main:app --port 8000
npm test -w uis/web
npm run typecheck
```

Last updated: 2026-09-23
