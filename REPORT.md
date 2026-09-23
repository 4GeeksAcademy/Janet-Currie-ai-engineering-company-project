# REPORT.md — Frontend performance and Web Vitals

Corrections applied after the baseline in [`AUDIT.md`](AUDIT.md). Same protocol, same URLs/modes, production `next start` (not Compose `next dev`). One Lighthouse pass per cell.

Optional Lighthouse skills were not installed.

## Corrections applied

### Website (`uis/website`)

| Finding | Change | Files |
|---------|--------|-------|
| W1 mobile TBT / oversized client tree | Header + Hero stay a client island. Why HealthCore, Services, Locations, Contact, Footer, and the quick-help bar are Server Components. `lang` comes from the `hc_lang` cookie so EN/ES still works without hydrating those sections. | `src/app/page.tsx`, `src/app/layout.tsx`, `src/components/HomePage.tsx`, `src/components/providers/LanguageProvider.tsx`, section files |
| W1 appointment modal JS | `AppointmentModal` loads only after the user opens it (`next/dynamic`, `ssr: false`). | `src/components/HomePage.tsx` |
| W1 (rejected) | `next/dynamic` of below-fold sections delayed LCP and did not raise Performance. Dropped. | — |

`html lang` is set from the same cookie on the server. Chrome (nav, hero, toggle) updates immediately; below-fold copy refreshes via `router.refresh()`.

Home route is now **dynamic** because it reads `cookies()`. Lab TTFB stayed short (10–20 ms → 30 ms).

### Staff UI (`uis/web`)

| Finding | Change | Files |
|---------|--------|-------|
| B1 contrast | Role label `text-slate-400` → `text-slate-600` (~7:1 on white). Sidebar `text-slate-400` on slate-950 left alone (not flagged). | `src/components/BackofficeShell.tsx` |
| B2 `/auth/me` on pathname | Not changed. Lab Performance was already 100. | — |

No API or backend contract changes. No content removed to inflate scores. Staff app is not indexed.

## Refactor shipped

Two candidates were documented in `AUDIT.md`. Both were implemented. The tested extraction is the staff hook.

### `LangToggle` (website)

- **Was:** duplicated EN/ES buttons inside `Header.tsx`.
- **Now:** [`uis/website/src/components/ui/LangToggle.tsx`](uis/website/src/components/ui/LangToggle.tsx), used in desktop and mobile chrome.
- **Not claimed** as a Lighthouse delta.

### `useAsyncResource` (staff UI) — tested hook

- **Was:** copy-pasted `useCallback` / `useEffect` / `toUserMessage` loaders in `MedicalSuppliesList` and `MovementHistory`.
- **Now:** [`uis/web/src/lib/useAsyncResource.ts`](uis/web/src/lib/useAsyncResource.ts) → `{ data, error, loading, reload }`.
- **Tests:** [`uis/web/src/lib/__tests__/useAsyncResource.test.ts`](uis/web/src/lib/__tests__/useAsyncResource.test.ts) (success, HTTP error mapping, retry). Inventory list tests still cover empty/error/retry UI.
- **Not claimed** as the operations Accessibility gain. `SupplierDirectory` still has its own mutate-in-place loader.

## Before / after

INP is **N/A** on all lab runs. FID proxy is Max Potential FID. TTFB is `server-response-time` (root document).

### Website home `http://127.0.0.1:3000/`

| Mode | Phase | Perf | A11y | BP | SEO | LCP | TBT | CLS | FID | TTFB | Screenshot |
|------|-------|------|------|----|-----|-----|-----|-----|-----|------|------------|
| desktop | before | 100 | 100 | 100 | 100 | 0.4 s | 70 ms | 0 | 120 ms | 20 ms | `audit/before/website-home-desktop-before.png` |
| desktop | after | 100 | 100 | 100 | 100 | 0.4 s | 40 ms | 0 | 90 ms | 30 ms | `audit/after/website-home-desktop-after.png` |
| mobile | before | **94** | 100 | 100 | 100 | 1.3 s | 300 ms | 0 | 360 ms | 10 ms | `audit/before/website-home-mobile-before.png` |
| mobile | after | **96** | 100 | 100 | 100 | 1.7 s | 220 ms | 0 | 270 ms | 30 ms | `audit/after/website-home-mobile-after.png` |

**Independent website gain:** mobile Performance **94 → 96** (TBT 300 ms → 220 ms; unused JS estimate 41 KiB → 21 KiB). Desktop stayed 100; TBT 70 ms → 40 ms.

Page JS on `next build`: 8.83 kB → 3.9 kB first-party route size; First Load JS 111 kB → 106 kB.

### Staff operations `http://127.0.0.1:3001/operations` (authenticated)

| Mode | Phase | Perf | A11y | BP | SEO | LCP | TBT | CLS | FID | TTFB | Screenshot |
|------|-------|------|------|----|-----|-----|-----|-----|-----|------|------------|
| desktop | before | 100 | **95** | 100 | 100 | 0.4 s | 0 ms | 0 | 50 ms | 0 ms | `audit/before/web-operations-desktop-before.png` |
| desktop | after | 98 | **100** | 100 | 100 | 0.4 s | 130 ms | 0 | 190 ms | 0 ms | `audit/after/web-operations-desktop-after.png` |

Confirmed `finalDisplayedUrl` is `/operations` (not `/login`) in both JSON reports. Thumbnail in the after report shows the operations dashboard.

**Independent staff gain:** Accessibility **95 → 100** (contrast failure on ` · admin` gone). Performance 100 → 98 is lab TBT noise on an already-green score; the contrast change is not a JS-size change.

## Impact

- Public site hydrates less work on mid-tier mobile (TBT and unused JS down). Full landing content still SSR and crawlable.
- Staff can read the signed-in role in the header.
- Inventory lists share one load/error/retry path.

## Leftover limits

- Framework unused JS remains in shared Next/React chunks (`255-*.js`, `4bd1b696-*.js`). Not removable without dropping React.
- Website home is dynamic (`cookies()`). Fine on localhost; a CDN/static host would need a different lang strategy (static `/` + `/es`, or CSS dual markup) to restore a prerendered HTML shell.
- Mobile LCP 1.3 s → 1.7 s (still a passing LCP score). Not chased further; Performance still rose on TBT.
- Staff `/auth/me` on every pathname was left as-is.
- `SupplierDirectory` was not migrated onto `useAsyncResource`.
- No RUM, CDN, or Lighthouse CI in this iteration.
- INP not measured (lab page-load only).

## Regression checks

| Check | Result |
|-------|--------|
| `npm run typecheck` | pass |
| `npm run lint -w uis/website` | pass (no warnings) |
| `npm run lint -w uis/web` | pass (no warnings) |
| `npm test -w uis/web` | 37 passed (was 34; +3 hook tests). `useAsyncResource.ts` 100% statements |
| `npm run build -w uis/website` | pass; `/` is ƒ dynamic, 3.9 kB + 106 kB first load |
| `npm run build -w uis/web` | pass |
| Smoke `GET /` | 200; English default; `Cookie: hc_lang=es` returns Spanish section titles |
| Smoke browser | Home, nav, EN/ES toggle (chrome immediate, sections after refresh), contact links |
| Smoke `/operations` via authenticated Lighthouse | URL `/operations`; panels visible in report filmstrip |
| Hydration | No console errors observed during the browser smoke. Cursor `data-cursor-ref` attributes can still appear in the IDE browser only |

No commit in this iteration (not requested).
