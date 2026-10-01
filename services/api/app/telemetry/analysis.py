"""Operational telemetry metrics. SQL filter then Pandas; no Python metric loops."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Sequence

import httpx
import pandas as pd

Loader = Callable[[datetime, datetime, Sequence[str] | None], pd.DataFrame]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["timestamp", "event_type", "level", "value", "tags"])


def load_from_supabase(
    start: datetime, end: datetime, event_types: Sequence[str] | None
) -> pd.DataFrame:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        return _empty()
    params: list[tuple[str, str]] = [
        ("timestamp", f"gte.{start.isoformat()}"),
        ("timestamp", f"lt.{end.isoformat()}"),
        ("select", "timestamp,event_type,level,value,tags"),
    ]
    if event_types:
        listed = ",".join(event_types)
        params.append(("event_type", f"in.({listed})"))
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    response = httpx.get(
        f"{url}/rest/v1/telemetry_events",
        headers=headers,
        params=params,
        timeout=20.0,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return _empty()
    return pd.DataFrame(rows)


_loader: Loader = load_from_supabase


def set_loader(fn: Loader | None) -> None:
    global _loader
    _loader = fn or load_from_supabase


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    out["date"] = out["timestamp"].dt.date.astype(str)
    return out


def events_per_day(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    df = _prepare(_loader(start_date, end_date, None))
    if df.empty:
        return []
    grouped = df.groupby(["date", "event_type"], as_index=False).agg(
        count=("event_type", "count")
    )
    return grouped.to_dict(orient="records")


def error_rate_by_type(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    df = _prepare(_loader(start_date, end_date, None))
    if df.empty:
        return []
    work = df.assign(is_error=(df["level"].eq("error") | df["event_type"].eq("frontend_error_raised")).astype(int))
    grouped = work.groupby(["date", "event_type"], as_index=False).agg(
        total=("is_error", "count"),
        errors=("is_error", "sum"),
    )
    grouped["error_rate"] = grouped["errors"] / grouped["total"]
    return grouped[["date", "event_type", "errors", "total", "error_rate"]].to_dict(orient="records")


def latency_by_day(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    df = _prepare(_loader(start_date, end_date, ("api_latency_recorded",)))
    if df.empty:
        return []
    work = df.dropna(subset=["value"])
    if work.empty:
        return []
    grouped = work.groupby("date", as_index=False).agg(mean_ms=("value", "mean"), samples=("value", "count"))
    return grouped.to_dict(orient="records")


def auth_failure_rate(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    df = _prepare(
        _loader(start_date, end_date, ("user_login_failed", "user_login_succeeded"))
    )
    if df.empty:
        return []
    work = df.assign(
        failed=df["event_type"].eq("user_login_failed").astype(int),
        attempts=1,
    )
    grouped = work.groupby("date", as_index=False).agg(
        failed=("failed", "sum"),
        attempts=("attempts", "sum"),
    )
    grouped["failure_rate"] = grouped["failed"] / grouped["attempts"]
    return grouped.to_dict(orient="records")


def build_metrics(start_date: datetime, end_date: datetime) -> dict[str, list[dict[str, Any]]]:
    return {
        "events_per_day": events_per_day(start_date, end_date),
        "error_rate_by_type": error_rate_by_type(start_date, end_date),
        "latency_by_day": latency_by_day(start_date, end_date),
        "auth_failure_rate": auth_failure_rate(start_date, end_date),
    }
