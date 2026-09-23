# Progress — Active iteration

## Current state

infra-40 Compose stack is implemented, verified, and archived. Shipped in `c96f167`. Phase guide lives in this archive as [`Docker-Context.md`](Docker-Context.md).

## Completed (standing)

- Public site, staff UI, incident CLI, supplier directory, staff JWT auth, error handling, bullet-proof tests, inventory API (HCR-0188), inventory backoffice UI.
- Docker artifacts: `docker-compose.yml`, `uis/Dockerfile`, `uis/start.sh`, `uis/.dockerignore`, `services/Dockerfile`, `services/.dockerignore`, root `.dockerignore`, `.env.example`, gitignored `.env`.
- CORS reads `CORS_ORIGINS`; `services/api/requirements.txt` includes `sqlmodel` and `psycopg[binary]`.

## Validation results

HCR-0188 (2026-09-18): 16 inventory pytest passed; 96 full pytest; compileall ok; live seed 6/4/3 gloves 105; live `/docs` + HTTP smoke. Details in [`TESTING.md`](../TESTING.md).

Inventory UI (2026-09-18): `npm test -w uis/web` 34 passed; lint clean; build and typecheck passed; live smoke of four `/backoffice/inventory/...` routes. Shipped in `afb1bed`. Durable notes: [`implementation-memory/inventory-backoffice-ui.md`](implementation-memory/inventory-backoffice-ui.md).

infra-40 (2026-09-18):

- `docker compose config` ok; `.env` gitignored/untracked; Dockerfiles/Compose/`.env.example` contain only placeholders (`SECRET_KEY=change-me-in-local-dev`). Container-internal `localhost` is not used for service DNS.
- `docker compose up --build`: images `ai-engineering-company-project-ui` and `-backend`; network `healthcore_dev`; ports 3000/3001/8000.
- Host: website `GET /` 200 on 3000; staff UI 200 on 3001; `GET /health` `{"status":"ok"}` and `/docs` 200 on 8000.
- UI container: `wget -qO- http://backend:8000/health` → `{"status":"ok"}`.
- Browser login as local admin against `localhost:8000`; inventory products page listed the six seeded supplies (after `python -m app.inventory.seed` in the backend container).
- Hot reload: website and `uis/web` recompiled after bind-mount edits; uvicorn WatchFiles reloaded `app/main.py`. Probe comments restored.
- Host regression: `npm run typecheck` exit 0; `npm test -w uis/web` 34 passed; `cd services/api && uv run pytest` 99 passed (includes 3 CORS tests).
- First Next compile after boot is slow (~30–75s). `@testing-library/jest-dom@7` warns EBADENGINE (wants Node 22; image is Node 20) — install still succeeds.
- `RESEND_API_KEY` empty and `DATABASE_URL` empty (sqlite in `data/`) still boot. No extra DB/mail containers.

## Blockers

- None for Compose start. Supabase MCP SQL still fails password auth; live inventory in this stack used sqlite because `DATABASE_URL` is empty.
- Docker Desktop must be running (`~/.docker/run/docker.sock`). It was started during validation.

## Next steps

1. Closed. Next phase is `Performance-Web-Vitals-Context.md` on branch `Performance-Web-Vitals`.

## Run commands (durable)

```bash
# Compose (repo root; copy .env.example → .env first)
docker compose up --build

# Optional one-time seed inside the backend container
docker compose exec backend python -m app.auth.seed
docker compose exec backend python -m app.inventory.seed

cd services/api
uv sync --group dev
uv run pytest
uv run seed-auth
uv run seed-inventory
uv run uvicorn app.main:app --reload --port 8000

npm test -w uis/web
npm run typecheck -w uis/web
npm run lint -w uis/web
npm run build -w uis/web
npm run dev -w uis/web
```

Last updated: 2026-09-21
