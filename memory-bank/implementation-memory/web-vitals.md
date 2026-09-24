# Web Vitals audit

## Purpose

Evidence-based Lighthouse / Web Vitals audit of the public site (`uis/website`) and staff UI (`uis/web`) so each frontend is demonstrably faster or more accessible without removing required UI.

## Final Behavior

- Website home hydrates Header/Hero as a client island. Why HealthCore, Services, Locations, Contact, Footer, and the quick-help bar are Server Components. EN/ES uses the `hc_lang` cookie plus `router.refresh()` for below-fold copy. The appointment modal loads only after open.
- Staff header role label uses `text-slate-600` (contrast ~7:1 on white).
- `LangToggle` is a shared website component. `useAsyncResource` loads inventory lists with shared error/retry handling.
- Lab: website mobile Performance 94 → 96; staff `/operations` Accessibility 95 → 100.

## Architecture and Data Flow

Production `next build` + `next start` (not Compose `next dev`) for comparable scores. Public `/` reads `hc_lang` and is dynamic. Staff `/operations` is client-gated JWT (`healthcore_access_token`); Lighthouse injects the token via CDP and does not print it.

## Important Files

- `AUDIT.md`, `REPORT.md`
- `audit/before/`, `audit/after/`, `audit/lh-auth.mjs`
- `uis/website/src/app/{page,layout}.tsx`, `uis/website/src/components/HomePage.tsx`
- `uis/website/src/components/ui/LangToggle.tsx`
- `uis/web/src/components/BackofficeShell.tsx`
- `uis/web/src/lib/useAsyncResource.ts`

## Interfaces and Contracts

- Cookie: `hc_lang=en|es` (path `/`, SameSite=Lax)
- Staff token key: `healthcore_access_token`
- Audited URLs: `http://localhost:3000/` (desktop + mobile), `http://localhost:3001/operations` (desktop, authenticated)

## Decisions and Constraints

- Staff app is `uis/web`, not leftover `uis/backoffice`.
- Do not mix Compose `dev` scores with production `start` scores.
- Do not install optional Lighthouse skills unless authorized.
- Do not use `next/dynamic` for below-fold marketing sections (delayed LCP).
- Do not duplicate EN/ES markup with CSS `display:none` (grew HTML and delayed LCP).
- Freeze `audit/before/` once implementation starts on a future re-audit.

## Validation

2026-09-23 (`ebec7d6`): typecheck; lint both UIs; 37 Jest (hook 100% coverage); both `next build`s; Lighthouse after matrix; browser EN/ES smoke; authenticated `/operations` filmstrip.

## Maintenance Notes

Home is dynamic because of `cookies()`. Framework unused JS in shared Next/React chunks remains. `SupplierDirectory` was not migrated onto `useAsyncResource`. INP is N/A on lab page-load runs.
