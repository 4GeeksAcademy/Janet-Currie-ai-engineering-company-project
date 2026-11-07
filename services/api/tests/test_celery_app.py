"""Celery configuration is driven by REDIS_URL."""

from __future__ import annotations

import os

import pytest

from app.celery_app import (
    RESULT_EXPIRES_SECONDS,
    TASK_MAX_RETRIES,
    TASK_SOFT_TIME_LIMIT,
    TASK_TIME_LIMIT,
    VISIBILITY_TIMEOUT_SECONDS,
    BrokerUnavailableError,
    celery_app,
    configure_celery,
    require_redis_url,
)
from app.tasks.pipeline_run import enqueue_pipeline_run, run_clinic_supply_pipeline


def test_redis_url_is_broker_and_backend_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://example.invalid:6379/0")
    configure_celery(celery_app)
    assert celery_app.conf.broker_url == "redis://example.invalid:6379/0"
    assert celery_app.conf.result_backend == "redis://example.invalid:6379/0"


def test_json_started_late_ack_retry_and_limits() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.enable_utc is True
    assert celery_app.conf.result_expires == RESULT_EXPIRES_SECONDS
    assert celery_app.conf.broker_transport_options["visibility_timeout"] == (
        VISIBILITY_TIMEOUT_SECONDS
    )
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_reject_on_worker_lost is False
    assert run_clinic_supply_pipeline.acks_late is True
    assert run_clinic_supply_pipeline.max_retries == TASK_MAX_RETRIES == 3
    assert run_clinic_supply_pipeline.soft_time_limit == TASK_SOFT_TIME_LIMIT
    assert run_clinic_supply_pipeline.time_limit == TASK_TIME_LIMIT


def test_missing_redis_url_fails_require(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(BrokerUnavailableError):
        require_redis_url()
    with pytest.raises(BrokerUnavailableError):
        enqueue_pipeline_run("2026-07-01")


def test_invalid_redis_url_fails_require(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "not-a-url")
    with pytest.raises(BrokerUnavailableError):
        require_redis_url()


def test_helpers_keep_redis_url_for_imports() -> None:
    assert os.environ.get("REDIS_URL", "").startswith("redis://")


def test_real_redis_accepts_apply_async() -> None:
    import redis as redis_lib

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_lib.Redis.from_url(url, socket_connect_timeout=1).ping()
    except Exception:
        pytest.skip("Redis is not reachable")
    configure_celery(celery_app, url=url)
    result = run_clinic_supply_pipeline.apply_async(kwargs={"month_start": "2026-07-01"})
    assert result.id
    with celery_app.connection_for_write() as conn:
        conn.default_channel.queue_purge("celery")
