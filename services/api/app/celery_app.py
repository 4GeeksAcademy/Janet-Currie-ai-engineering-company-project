"""Celery application. Importing this module must not run ETL or open PostgREST."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from celery import Celery

# Mirror app.main so the worker can import pipelines.pipeline.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO_ROOT / "scripts"
_DATA = _REPO_ROOT / "data"
for _path in (str(_SCRIPTS), str(_DATA)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

TASK_MAX_RETRIES = 3
TASK_SOFT_TIME_LIMIT = 840
TASK_TIME_LIMIT = 900
RESULT_EXPIRES_SECONDS = 86400
VISIBILITY_TIMEOUT_SECONDS = 3600
WORKER_CONCURRENCY = 1


class BrokerUnavailableError(RuntimeError):
    """REDIS_URL is missing/malformed or the broker cannot be reached."""


def redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def require_redis_url() -> str:
    url = redis_url()
    if not url or "://" not in url:
        raise BrokerUnavailableError("REDIS_URL is missing or malformed")
    return url


def _running_as_worker_or_flower() -> bool:
    joined = " ".join(sys.argv).lower()
    return "worker" in joined or "flower" in joined


def configure_celery(app: Celery | None = None, *, url: str | None = None) -> Celery:
    target = app or celery_app
    resolved = url if url is not None else redis_url()
    target.conf.update(
        broker_url=resolved or None,
        result_backend=resolved or None,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        timezone="UTC",
        enable_utc=True,
        result_expires=RESULT_EXPIRES_SECONDS,
        broker_transport_options={"visibility_timeout": VISIBILITY_TIMEOUT_SECONDS},
        worker_prefetch_multiplier=1,
        worker_concurrency=WORKER_CONCURRENCY,
        task_reject_on_worker_lost=False,
        include=["app.tasks.pipeline_run"],
    )
    return target


celery_app = Celery("healthcore")
configure_celery(celery_app)

if _running_as_worker_or_flower():
    require_redis_url()
    configure_celery(celery_app)
