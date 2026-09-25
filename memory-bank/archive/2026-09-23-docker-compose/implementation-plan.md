# Implementation plan — Docker Compose development environment (infra-40)

Two Compose services from the repo root: `ui` (website 3000 + staff `uis/web` 3001) and `backend` (`services/api` on 8000), on named network `healthcore_dev`. Staff UI is `uis/web`, not leftover `uis/backoffice`. No extra DB/mail containers.

## Approach

- Dockerfiles at `uis/Dockerfile` and `services/Dockerfile`; Compose `build.context` is the repo root so the npm workspace lockfile and `scripts/` (`parents[3]` from `app/main.py`) are visible.
- UI: `node:20-alpine`, `npm ci -w uis/website -w uis/web`, `uis/start.sh` runs both `next dev` processes bound to `0.0.0.0`. Named volumes protect `node_modules` from bind mounts.
- Backend: `python:3.12-slim-bookworm`, `uv pip install --system -r requirements.txt`, uvicorn `--reload --reload-dir app`. Named volume hides container `.venv` from the host.
- Browser `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; only container-originated calls use `http://backend:8000`.
- CORS from `CORS_ORIGINS`. Seed with `docker compose exec backend python -m app.auth.seed` (not `uv run`).

## Todos (completed)

1. Refresh `requirements.txt` (`sqlmodel`, `psycopg[binary]`); parse `CORS_ORIGINS` in `app/main.py`.
2. UI Dockerfile, `start.sh`, `.dockerignore`.
3. Backend Dockerfile, `.dockerignore`, `scripts/` layout, data bind-mount.
4. Root `docker-compose.yml`, named network, `.env.example`, gitignored `.env`.
5. Compose up, DNS health, login/inventory, hot reload, host typecheck/pytest.
