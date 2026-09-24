# Tech updates — Web Vitals

- Lighthouse 13.5.0 CLI + Chrome 153; lab INP N/A; TTFB from `server-response-time`; Max Potential FID as FID proxy.
- Next.js App Router: website 15.5.23, staff UI 15.2.4. Home became dynamic after `cookies()` for `hc_lang`.
- Staff Lighthouse used CDP `localStorage` inject (`audit/lh-auth.mjs`) with `--disable-storage-reset`; token never written to the repo.
- `next/dynamic` on below-fold sections delayed LCP and was dropped. Dual-language CSS markup grew HTML and was dropped.
