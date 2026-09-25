# Implementation plan — Web Vitals (final)

Measure → analyse → fix → measure again on `uis/website` and `uis/web` using production `next start`.

1. Protocol in `AUDIT.md`; `audit/before/` and `audit/after/`.
2. Baseline Lighthouse: website home desktop/mobile; authenticated staff `/operations` desktop.
3. Map findings to files; document two refactor candidates.
4. Targeted fixes only (no score inflation, no API changes).
5. Ship one shared extraction with tests (`useAsyncResource`; also `LangToggle`).
6. After matrix, `REPORT.md`, typecheck/lint/test/build/smoke.

Out of scope: redesign, backend/DB, RUM/CDN, optional skill install, `uis/backoffice`, mixing Compose `dev` with production scores.
