# `uis` folder

This folder contains **all the user interfaces** related to the company for the cross-functional AI Engineering project (for example: web applications, internal dashboards, customer portals, Streamlit/Gradio apps, etc.).

Each subfolder inside `uis/` must correspond to **one specific user interface** (for example: `website`, `backoffice`) and include its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all the frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._

## Active apps (Next.js)

From the **repository root** (npm workspaces):

```bash
npm install
npm run dev:website      # http://localhost:3000 — public HealthCore site
npm run dev:backoffice   # http://localhost:3001 — HealthCore Digital backoffice
npm run typecheck
```

| App | Path | Purpose |
|-----|------|---------|
| Public website | [`website/`](website/) | Milestone 1 corporate site migrated to Next.js + reusable React components |
| Backoffice | [`backoffice/`](backoffice/) | Internal layout, welcome screen, operations analytics importing Milestone 2 from `src/` |

Backoffice imports domain logic via `@healthcore/*` → repo `src/` (import, do not copy).

## Milestone 1 archive (static)

Legacy static landing (kept for reference; prefer `website/`):

```bash
npx --yes serve uis -l 5500
```

Then open `http://localhost:5500`.

- [index.html](index.html) — original landing page
- [application.html](application.html) — patient enquiry form
- [validation.js](validation.js) — client-side validation

## Programming fundamentals demo

[`programming-fundamentals/`](programming-fundamentals/) — Milestone 2 browser demo (console/panel demo). Prefer the backoffice operations view for the Next.js integration of the same `src/` modules.
