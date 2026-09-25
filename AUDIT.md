# AUDIT.md — Frontend performance and Web Vitals

Pre-change analysis and measurement record for the HealthCore public site (`uis/website`) and staff UI (`uis/web`). Staff app is **not** leftover `uis/backoffice`.

Optional Lighthouse skills (`core-web-vitals`, `performance`, `web-perf`) were **not** installed (no user authorization). Analysis is repository inspection plus Lighthouse lab runs.

## Measurement protocol

Defined **before** the first run. The same protocol is used for baseline and after measurements.

### Runtime (production-like, both rounds)

Compose `docker compose up` runs `next dev` and is **not** used for these audits. Host production builds:

```bash
npm run build -w uis/website && npm run start -w uis/website   # http://localhost:3000
npm run build -w uis/web && npm run start -w uis/web           # http://localhost:3001
cd services/api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Do not compare a `dev` baseline with a `start` after.

### Tooling

- Chrome DevTools Lighthouse engine via the `lighthouse` CLI (same categories as the panel: Performance, Accessibility, Best Practices, SEO).
- Screenshots of each HTML report saved under `audit/before/` then `audit/after/`.
- Format: PNG. Names identify app, page, mode, phase.

### Repeat policy

One pass per cell. Repeat only if the run is obviously broken (wrong URL, login bounce, compile error, extension noise). Record the replacement and why. Do not cherry-pick the best of several healthy runs.

### Cache and throttling

- Fresh Lighthouse session per URL/mode (`--disable-storage-reset` is **not** used, except staff UI must keep `localStorage` JWT — see auth).
- Desktop: Lighthouse desktop preset.
- Mobile: Lighthouse mobile preset (simulated throttling).
- Categories: performance, accessibility, best-practices, seo.

### Staff UI authentication

Protected routes use client-side JWT (`localStorage` key `healthcore_access_token`). There is no Next middleware. Baseline and after runs:

1. API running on `http://localhost:8000`.
2. Login as local admin (`admin@healthcore.example`) or inject a valid token.
3. Confirm the loaded URL is `/operations`, not `/login`, before measuring.
4. Screenshots must not include tokens, passwords, or live PHI. Seed/dev data only.

For CLI runs, pass `--extra-headers` is insufficient for `localStorage`. Use a Chrome user-data directory that already has the token, or run Lighthouse against a page after a scripted login.

### Environment (baseline 2026-09-23)

| Field | Value |
|-------|--------|
| Date | 2026-09-23 |
| Host | macOS 14 (darwin 23.6.0), local loopback |
| Browser / Lighthouse | Google Chrome 153.0.8010.53 + Lighthouse 13.5.0 CLI (same engine as DevTools panel) |
| Website command | `npm run build -w uis/website` then `npm run start -w uis/website` |
| Staff UI command | `npm run build -w uis/web` then `npm run start -w uis/web` |
| API | `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` (default) |
| Cache | Default Lighthouse storage reset on public pages. Staff run used `--disable-storage-reset` after CDP injected `healthcore_access_token` (token never written to the repo). |
| Extensions | Headless Chrome, no user extensions |
| Anomalies | Website desktop/mobile: one pass each. Staff `/operations`: first CDP attach failed (`Page.enable`); one retry after flatten `sessionId` fix. No cherry-picking of scores. |

### Screenshot filenames

| File | App | URL | Mode | Phase |
|------|-----|-----|------|-------|
| `audit/before/website-home-desktop-before.png` | website | `http://localhost:3000/` | desktop | baseline |
| `audit/before/website-home-mobile-before.png` | website | `http://localhost:3000/` | mobile | baseline |
| `audit/before/web-operations-desktop-before.png` | web | `http://localhost:3001/operations` | desktop | baseline |
| `audit/after/website-home-desktop-after.png` | website | `http://localhost:3000/` | desktop | after |
| `audit/after/website-home-mobile-after.png` | website | `http://localhost:3000/` | mobile | after |
| `audit/after/web-operations-desktop-after.png` | web | `http://localhost:3001/operations` | desktop | after |

Optional extra (only if `/operations` is already too green to improve honestly): `web-suppliers-desktop-*` at `http://localhost:3001/suppliers`. Same URL/mode before and after.

## Audit scope

### Corporate website (`uis/website`)

- **Home** `http://localhost:3000/` — required. Only public App Router page; `#locations` / `#services` are in-page anchors, not separate Lighthouse documents.
- Desktop **and** mobile.

Why: marketing landing page; visual complexity (hero, cards, locations table, enquiry form); SEO matters.

### Staff UI (`uis/web`)

- **Operations** `http://localhost:3001/operations` — representative dashboard: Milestone 2 analytics panels and large JSON `<pre>` via `@healthcore/*`.
- Desktop (staff usage). Brief requires both modes only for the public site.

Why: element-heavy operational view used daily; client-bundled sample data + charts-as-JSON.

## Baseline results

Collected **before** application code changes. JSON/HTML companions of each PNG live in the same folder (optional extra evidence).

INP is **N/A** on all lab runs (Lighthouse 13.5 does not emit `interaction-to-next-paint` without a user-flow interaction). FID proxy recorded as Max Potential FID. TTFB is `server-response-time` (root document).

| App | Page | Mode | Perf | A11y | BP | SEO | LCP | CLS | INP/FID | TTFB | Screenshot |
|-----|------|------|------|------|----|-----|-----|-----|---------|------|------------|
| website | home | desktop | 100 | 100 | 100 | 100 | 0.4 s | 0 | N/A (max FID 120 ms) | 20 ms | `audit/before/website-home-desktop-before.png` |
| website | home | mobile | 94 | 100 | 100 | 100 | 1.3 s | 0 | N/A (max FID 360 ms) | 10 ms | `audit/before/website-home-mobile-before.png` |
| web | operations | desktop | 100 | 95 | 100 | 100 | 0.4 s | 0 | N/A (max FID 50 ms) | 0 ms | `audit/before/web-operations-desktop-before.png` |

Confirmed staff `finalDisplayedUrl` is `http://127.0.0.1:3001/operations` (not `/login`).

## Findings and root causes

### W1 — Website mobile Total Blocking Time / unused JavaScript

- **App/page:** `uis/website` home, mobile (Performance 94). Desktop already 100.
- **Observed:** TBT 300 ms (score 0.79), max potential FID 360 ms, unused JS ~41 KiB (`255-*.js`, `4bd1b696-*.js`), render-blocking CSS ~6 KiB / 193 ms. LCP 1.3 s and CLS 0 are healthy.
- **Root cause:** [`uis/website/src/components/HomePage.tsx`](uis/website/src/components/HomePage.tsx) is `"use client"` and statically imports Header, Hero, every section, enquiry/contact, footer, and `AppointmentModal`. The whole landing tree hydrates as one client bundle even though only language toggle, menu, modal, and the enquiry form need interactivity. [`uis/website/src/app/page.tsx`](uis/website/src/app/page.tsx) only re-exports that client tree.
- **User impact:** Main-thread work on mid-tier mobile delays tap responsiveness after first paint.
- **Priority:** High — only website score below 100 and the assigned Performance lever.
- **Correction:** Keep Header + Hero as the client island; render Why/Services/Locations/Contact/Footer as Server Components with `lang` from the `hc_lang` cookie. Lazy-load `AppointmentModal` only when opened. `next/dynamic` on below-fold sections was tried and dropped — it delayed LCP without a Performance gain.
- **Validate:** Re-run mobile (and desktop to watch for regressions) on `http://127.0.0.1:3000/`. Expect Performance and/or TBT to improve.
- **Tradeoff:** Home becomes dynamic (`cookies()`). Language toggle updates chrome immediately and refreshes server sections. TTFB rose slightly in lab (10 ms → 30 ms). Do not remove content.

### W2 — Website SEO metadata gaps (not a failing audit)

- **Observed:** SEO 100 from title + description + crawlable HTML. No `robots.ts`, `sitemap.ts`, Open Graph, or `metadataBase` in [`uis/website/src/app/layout.tsx`](uis/website/src/app/layout.tsx).
- **Priority:** Low for this iteration — cannot raise an already-100 SEO score; skip to avoid claiming a fake win.

### B1 — Staff UI color contrast on the role label

- **App/page:** `uis/web` `/operations`, desktop (Accessibility 95).
- **Observed:** `color-contrast` fails on `<span class="text-slate-400"> · admin</span>` — foreground `#94a3b8` on `#ffffff`, ratio 2.56, need 4.5:1.
- **Root cause:** [`uis/web/src/components/BackofficeShell.tsx`](uis/web/src/components/BackofficeShell.tsx) uses `text-slate-400` for the signed-in role next to the name.
- **User impact:** Low-vision staff cannot reliably read the role in the header (all protected pages).
- **Priority:** High — only failing category on the staff audit; required independent score gain.
- **Correction:** Use `text-slate-600` (`#475569`, ~7:1 on white). Do not lighten the sidebar (`text-slate-400` on `slate-950` is a different pair and was not flagged).
- **Validate:** Re-run desktop Lighthouse on `/operations`; Accessibility should rise if this is the only contrast failure.
- **Tradeoffs:** Slightly stronger header text; no functional change.

### B2 — Staff `/auth/me` on every pathname (not confirmed by lab scores)

- **File:** [`uis/web/src/components/AuthProvider.tsx`](uis/web/src/components/AuthProvider.tsx) `useEffect(..., [refresh, pathname])`.
- **Lab:** Operations Performance already 100, LCP 0.4 s. Not changing this unless a later run shows network delay. Documented only.

## Refactor analysis

Website and `uis/web` stay separate (no shared UI package).

### Candidate 1 — Website `LangToggle`

- **Locations:** local `LangToggle` in [`uis/website/src/components/sections/Header.tsx`](uis/website/src/components/sections/Header.tsx) used twice (desktop + mobile).
- **Shared:** EN/ES `aria-pressed` buttons and `setLang`.
- **Why extract:** One component file, one style/a11y contract, Header stays layout-only.
- **Interface:** `{ lang, setLang }` where `lang` is `"en" | "es"`.
- **Keep local:** mobile menu open state, appointment CTA copy.
- **Over-generalize risk:** putting it in `uis/web` (different chrome) — will not.
- **Implement:** extract to `uis/website/src/components/ui/LangToggle.tsx`. Maintainability only; do not attribute Lighthouse deltas to it.

### Candidate 2 — Staff `useAsyncResource` (ship this as the tested hook)

- **Locations:** identical load/error/retry in [`MedicalSuppliesList.tsx`](uis/web/src/components/inventory/MedicalSuppliesList.tsx), [`MovementHistory.tsx`](uis/web/src/components/inventory/MovementHistory.tsx), and the list fetch in [`SupplierDirectory.tsx`](uis/web/src/components/SupplierDirectory.tsx).
- **Shared:** `useCallback`/`useEffect`, `toUserMessage`, loading flag, retry.
- **Why extract:** One place to keep abort/error handling consistent.
- **Interface:** `useAsyncResource<T>(loader: () => Promise<T>)` → `{ data, error, loading, reload }`.
- **Keep local:** table markup, supplier filters, form state.
- **Over-generalize risk:** a React Query replacement — keep the hook tiny.
- **Implement:** **yes**, with Jest. Maintainability; not claimed as the operations Accessibility gain.

## Agent-skill findings

None. Optional skills were not installed.

## Corrections planned (priority)

1. Website mobile TBT: shrink the client tree (server-rendered sections + deferred appointment modal).
2. Staff Accessibility: header role contrast `text-slate-600`.
3. Refactor: extract `useAsyncResource` (tested) and `LangToggle`.
4. Remeasure the same three cells. Keep only justified changes.

After scores, deltas, and leftover limits: [`REPORT.md`](REPORT.md).
