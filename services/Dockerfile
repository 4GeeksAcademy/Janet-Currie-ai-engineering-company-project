FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:0.7.0 /uv /usr/local/bin/uv

WORKDIR /app/services/api
COPY services/api/requirements.txt requirements.txt
RUN uv pip install --system -r requirements.txt

WORKDIR /app
COPY services/api services/api
COPY scripts scripts

WORKDIR /app/services/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]
