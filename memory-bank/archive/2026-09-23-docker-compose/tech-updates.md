# Tech updates — Docker Compose (infra-40)

## Topology

- Services: `ui`, `backend` (DNS name for other containers)
- Network: `healthcore_dev` (explicit `name: healthcore_dev`)
- Ports: `3000:3000`, `3001:3001`, `8000:8000`
- Images: `node:20-alpine`, `python:3.12-slim-bookworm` + `ghcr.io/astral-sh/uv:0.7.0`

## Files added

- `docker-compose.yml`, root `.dockerignore`, root `.env.example`
- `uis/Dockerfile`, `uis/start.sh`, `uis/.dockerignore`
- `services/Dockerfile`, `services/.dockerignore`
- `services/api/tests/test_cors.py`

## Application changes

- `services/api/app/main.py` — `cors_origins()` from `CORS_ORIGINS`
- `services/api/requirements.txt` — `sqlmodel`, `psycopg[binary]`
- Backend CMD: `uvicorn ... --reload --reload-dir app`
- Compose env: `WATCHFILES_FORCE_POLLING=true` for Docker Desktop on macOS

## Env / secrets

- No secrets in YAML or Dockerfiles
- Copy `.env.example` → gitignored `.env` before `docker compose up`
- Seed: `docker compose exec backend python -m app.auth.seed` then `python -m app.inventory.seed`

## Docs

- Phase guide moved from repo root into this archive
- Durable notes: `memory-bank/implementation-memory/docker-compose-dev.md`
- Shipped in `c96f167` on `milestone-5`
