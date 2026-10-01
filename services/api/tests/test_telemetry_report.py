"""Operational telemetry report metrics (Pandas, no Python aggregation loops)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd
import pytest

from app.cache import report_cache
from app.telemetry import analysis
from tests.helpers import client


def _frame() -> pd.DataFrame:
    day = datetime(2026, 9, 28, 12, tzinfo=timezone.utc).isoformat()
    return pd.DataFrame(
        [
            {
                "timestamp": day,
                "event_type": "page_viewed",
                "level": "info",
                "value": None,
                "tags": {},
            },
            {
                "timestamp": day,
                "event_type": "frontend_error_raised",
                "level": "error",
                "value": None,
                "tags": {},
            },
            {
                "timestamp": day,
                "event_type": "api_latency_recorded",
                "level": "info",
                "value": 40,
                "tags": {},
            },
            {
                "timestamp": day,
                "event_type": "user_login_failed",
                "level": "warn",
                "value": None,
                "tags": {},
            },
            {
                "timestamp": day,
                "event_type": "user_login_succeeded",
                "level": "info",
                "value": None,
                "tags": {},
            },
        ]
    )


@pytest.fixture(autouse=True)
def _loader() -> None:
    report_cache.clear()

    def load(_start: datetime, _end: datetime, types):
        df = _frame()
        if types:
            return df[df["event_type"].isin(list(types))].copy()
        return df.copy()

    analysis.set_loader(load)
    yield
    analysis.set_loader(None)
    report_cache.clear()


def test_report_shape_and_metrics() -> None:
    start = datetime(2026, 9, 28, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    response = client.get(
        "/telemetry/report",
        params={"start_date": start.isoformat(), "end_date": end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["period"]["from"].startswith("2026-09-28")
    metrics = body["metrics"]
    assert "events_per_day" in metrics
    assert "error_rate_by_type" in metrics
    assert "latency_by_day" in metrics
    assert "auth_failure_rate" in metrics
    assert metrics["auth_failure_rate"][0]["failure_rate"] == 0.5
    assert metrics["latency_by_day"][0]["mean_ms"] == 40


def test_report_cache_skips_second_load() -> None:
    start = datetime(2026, 9, 28, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    params = {"start_date": start.isoformat(), "end_date": end.isoformat()}
    with patch("app.routers.telemetry.build_metrics", wraps=analysis.build_metrics) as spy:
        first = client.get("/telemetry/report", params=params)
        second = client.get("/telemetry/report", params=params)
    assert first.json() == second.json()
    assert spy.call_count == 1


def test_empty_loader() -> None:
    analysis.set_loader(lambda *_args: pd.DataFrame())
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 2, tzinfo=timezone.utc)
    body = client.get(
        "/telemetry/report",
        params={"start_date": start.isoformat(), "end_date": end.isoformat()},
    ).json()
    assert body["metrics"]["events_per_day"] == []
