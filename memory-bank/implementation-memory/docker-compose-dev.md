# Docker Compose development environment

## Purpose

One-command local stack so website, staff UI, and FastAPI share Node/Python versions and a named Docker network (`infra-40`).

## Final Behavior

- `docker compose up` from the repo root starts `ui` (3000 + 3001) and `backend` (8000) on `healthcore_dev`.
- Host browser uses `http://localhost:8000`. Containers reach the API at `http://backend:8000`.
- Source bind mounts plus named `node_modules` / backend `.venv` volumes support hot reload without hiding image-installed deps.
- Empty `DATABASE_URL` uses sqlite under `services/api/data/`; empty `RESEND_API_KEY` still boots.

## Architecture and Data Flow

Host browser → published ports → Next dev servers in `ui` and uvicorn in `backend`. Staff JWT `fetch` stays client-side to `localhost:8000`. `app/main.py` still inserts repo-root `scripts/` via `Path(__file__).parents[3]`, so the backend image layout is `/app/services/api` plus `/app/scripts`.

## Important Files

- `docker-compose.yml`
- `uis/Dockerfile`, `uis/start.sh`, `uis/.dockerignore`
- `services/Dockerfile`, `services/.dockerignore`
- `.dockerignore`, `.env.example`
- `services/api/app/main.py` (`CORS_ORIGINS`)
- `services/api/requirements.txt`

## Interfaces and Contracts

- Compose service names: `ui`, `backend`
- Network name: `healthcore_dev`
- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- `CORS_ORIGINS` comma-separated; default `http://localhost:3001`, `http://127.0.0.1:3001`
- Seed inside the image: `python -m app.auth.seed` / `python -m app.inventory.seed` (system site-packages)

## Decisions and Constraints

- Do not set `NEXT_PUBLIC_*` to Docker DNS names.
- Do not revive `uis/backoffice` or add Postgres/mail containers for this stack.
- Do not put these Dockerfiles under `infra/`.
- Do not `uv run` seed commands in the backend container against the bind-mounted tree.

## Validation

Observed 2026-09-18: `docker compose config`; `compose up --build`; host 200 on 3000/3001/`/health`/`/docs`; `wget http://backend:8000/health` from `ui`; browser login + inventory list; hot reload; host typecheck, 34 Jest tests, 99 pytest. Shipped in `c96f167`.

## Maintenance Notes

First Next compile after boot can take 30–75s. Docker Desktop must be running. If WatchFiles stalls the worker on macOS, keep `WATCHFILES_FORCE_POLLING=true`. After changing Compose env, recreate the backend container.
