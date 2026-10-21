"""Read helpers for reporting tables. No KPI formulas."""

from __future__ import annotations

from datetime import date
from typing import Any

from pipelines.pipeline import latest_pipeline_run, list_clinic_month_rows


def _month_key(value: object) -> str:
    text = str(value)
    return text[:10]


def clinic_month_report(month_start: date | None) -> tuple[str | None, list[dict[str, Any]]]:
    if month_start is not None:
        key = month_start.isoformat()
        return key, list_clinic_month_rows(key)
    rows = list_clinic_month_rows(None)
    if not rows:
        return None, []
    latest = max(_month_key(row.get("month_start")) for row in rows)
    matched = [row for row in rows if _month_key(row.get("month_start")) == latest]
    return latest, matched


def latest_run() -> dict[str, Any] | None:
    return latest_pipeline_run()
