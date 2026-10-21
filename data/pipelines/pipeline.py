"""Monthly clinic supply performance: extract, transform, load (Prefect 3)."""

from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

if __name__ == "__main__":
    try:
        import prefect  # noqa: F401
    except ImportError:
        _venv_dir = Path(__file__).resolve().parents[2] / "services" / "api" / ".venv"
        _venv_py = _venv_dir / "bin" / "python"
        if _venv_py.exists() and Path(sys.prefix).resolve() != _venv_dir.resolve():
            os.execv(str(_venv_py), [str(_venv_py), *sys.argv])
        raise SystemExit("prefect is not installed; run `uv sync` in services/api")

import httpx
from prefect import flow, task

logger = logging.getLogger(__name__)

KPI_EVENT_TYPES = frozenset(
    {
        "inbound_order_created",
        "outbound_order_created",
        "stock_threshold_triggered",
        "supply_expiry_flagged",
    }
)
CURRENCY = {"US": "USD", "UK": "GBP"}
pipeline_lock = threading.Lock()

ExtractFn = Callable[[datetime, datetime], list[dict[str, Any]]]
LoadFn = Callable[[list[dict[str, Any]]], int]
InsertRunFn = Callable[[dict[str, Any]], None]
UpdateRunFn = Callable[[str, dict[str, Any]], None]
HeartbeatFn = Callable[[str], None]


class PipelineBusyError(Exception):
    """A clinic-supply pipeline run is already in progress."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def previous_utc_month(today: date | None = None) -> date:
    current = today or _utcnow().date()
    first = current.replace(day=1)
    last_prev = first - timedelta(days=1)
    return last_prev.replace(day=1)


def add_utc_months(month_start: date, months: int) -> date:
    year = month_start.year + (month_start.month - 1 + months) // 12
    month = (month_start.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def window_for_month(month_start: date) -> tuple[datetime, datetime]:
    """Inclusive start, exclusive end: month plus 7-day late-arrival lookback."""
    start = datetime(month_start.year, month_start.month, 1, tzinfo=timezone.utc)
    nxt = add_utc_months(month_start, 1)
    end = datetime(nxt.year, nxt.month, 1, tzinfo=timezone.utc) + timedelta(days=7)
    return start, end


def _tags(event: dict[str, Any]) -> dict[str, Any]:
    tags = event.get("tags")
    if isinstance(tags, dict):
        return dict(tags)
    props = event.get("properties") if isinstance(event.get("properties"), dict) else {}
    out = dict(props)
    if event.get("eventId") is not None:
        out.setdefault("eventId", event["eventId"])
    return out


def _event_id(event: dict[str, Any], tags: dict[str, Any]) -> str | None:
    raw = tags.get("eventId") or event.get("eventId")
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw)


def _clinic_id(tags: dict[str, Any]) -> str | None:
    raw = tags.get("clinic_id")
    try:
        number = int(raw)
    except (TypeError, ValueError):
        return None
    if number < 1 or number > 12:
        return None
    return str(number)


def _country(tags: dict[str, Any]) -> str | None:
    value = tags.get("country")
    if value in ("US", "UK"):
        return str(value)
    return None


def _timestamp(event: dict[str, Any]) -> datetime | None:
    raw = event.get("timestamp")
    if isinstance(raw, datetime):
        ts = raw
    elif isinstance(raw, str) and raw:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _positive_cost(tags: dict[str, Any]) -> float | None:
    raw = tags.get("unit_cost")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    if float(raw) <= 0:
        return None
    return float(raw)


def _positive_qty(tags: dict[str, Any]) -> int | None:
    raw = tags.get("quantity")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    qty = int(raw)
    if qty != raw or qty < 1:
        return None
    return qty


def transform_clinic_month_kpis(
    events: list[dict[str, Any]],
    window: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure KPI transform. window is unused in math; kept for cache-key/task I/O."""
    _ = window
    seen_ids: set[str] = set()
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    conflicted: set[tuple[str, str]] = set()
    clinic_country: dict[tuple[str, str], str] = {}
    extracted = len(events)
    quarantined = 0

    for event in events:
        event_type = event.get("event_type")
        if event_type not in KPI_EVENT_TYPES:
            quarantined += 1
            continue
        tags = _tags(event)
        eid = _event_id(event, tags)
        clinic = _clinic_id(tags)
        country = _country(tags)
        ts = _timestamp(event)
        if not eid or not clinic or not country or ts is None:
            quarantined += 1
            continue
        if eid in seen_ids:
            continue
        seen_ids.add(eid)
        if event_type == "inbound_order_created":
            if _positive_cost(tags) is None or _positive_qty(tags) is None:
                quarantined += 1
                continue
        month_start = date(ts.year, ts.month, 1).isoformat()
        country_key = (clinic, month_start)
        existing_country = clinic_country.get(country_key)
        if existing_country and existing_country != country:
            conflicted.add(country_key)
            quarantined += 1
            continue
        clinic_country[country_key] = country
        key = (clinic, country, month_start)
        row = groups.setdefault(
            key,
            {
                "clinic_id": clinic,
                "country": country,
                "month_start": month_start,
                "total_supply_cost": 0.0,
                "supply_consumption_count": 0,
                "critical_stockout_count": 0,
                "expiry_risk_count": 0,
                "currency": CURRENCY[country],
            },
        )
        if event_type == "inbound_order_created":
            row["total_supply_cost"] += _positive_cost(tags) * _positive_qty(tags)
        elif event_type == "outbound_order_created":
            row["supply_consumption_count"] += 1
        elif event_type == "stock_threshold_triggered":
            row["critical_stockout_count"] += 1
        elif event_type == "supply_expiry_flagged":
            row["expiry_risk_count"] += 1

    rows = []
    for (clinic, country, month_start), row in groups.items():
        if (clinic, month_start) in conflicted:
            quarantined += 1
            continue
        row["total_supply_cost"] = round(float(row["total_supply_cost"]), 2)
        rows.append(row)
    rows.sort(key=lambda item: (item["month_start"], item["clinic_id"]))
    return {
        "rows": rows,
        "events_extracted": extracted,
        "events_quarantined": quarantined,
    }


def _supabase_headers() -> tuple[str, dict[str, str]] | None:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        return None
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Profile": "reporting",
        "Content-Profile": "reporting",
    }


def extract_from_supabase(window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        logger.warning("clinic supply extract skipped: missing SUPABASE_URL or key")
        return []
    listed = ",".join(sorted(KPI_EVENT_TYPES))
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    response = httpx.get(
        f"{url}/rest/v1/telemetry_events",
        headers=headers,
        params=[
            ("timestamp", f"gte.{window_start.isoformat()}"),
            ("timestamp", f"lt.{window_end.isoformat()}"),
            ("event_type", f"in.({listed})"),
            ("select", "timestamp,event_type,tags"),
        ],
        timeout=20.0,
    )
    response.raise_for_status()
    rows = response.json()
    return rows if isinstance(rows, list) else []


def load_to_supabase(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    creds = _supabase_headers()
    if creds is None:
        logger.warning("clinic supply load skipped: missing SUPABASE_URL or key")
        return 0
    url, headers = creds
    headers = {
        **headers,
        "Prefer": "return=minimal,resolution=merge-duplicates",
    }
    payload = [{**row, "computed_at": _utcnow().isoformat()} for row in rows]
    response = httpx.post(
        f"{url}/rest/v1/monthly_clinic_supply_performance",
        headers=headers,
        json=payload,
        timeout=20.0,
    )
    response.raise_for_status()
    return len(rows)


def insert_run_supabase(row: dict[str, Any]) -> None:
    creds = _supabase_headers()
    if creds is None:
        return
    url, headers = creds
    headers = {**headers, "Prefer": "return=minimal"}
    response = httpx.post(
        f"{url}/rest/v1/pipeline_runs",
        headers=headers,
        json=row,
        timeout=20.0,
    )
    response.raise_for_status()


def update_run_supabase(run_id: str, fields: dict[str, Any]) -> None:
    creds = _supabase_headers()
    if creds is None:
        return
    url, headers = creds
    headers = {**headers, "Prefer": "return=minimal"}
    response = httpx.patch(
        f"{url}/rest/v1/pipeline_runs",
        headers=headers,
        params={"run_id": f"eq.{run_id}"},
        json=fields,
        timeout=20.0,
    )
    response.raise_for_status()


def list_kpi_rows_supabase(month_start: str | None) -> list[dict[str, Any]]:
    creds = _supabase_headers()
    if creds is None:
        return []
    url, headers = creds
    params: list[tuple[str, str]] = [
        ("select", "clinic_id,country,month_start,total_supply_cost,supply_consumption_count,critical_stockout_count,expiry_risk_count,currency"),
        ("order", "clinic_id.asc"),
    ]
    if month_start:
        params.append(("month_start", f"eq.{month_start}"))
    response = httpx.get(
        f"{url}/rest/v1/monthly_clinic_supply_performance",
        headers=headers,
        params=params,
        timeout=20.0,
    )
    response.raise_for_status()
    rows = response.json()
    return rows if isinstance(rows, list) else []


def latest_run_supabase() -> dict[str, Any] | None:
    creds = _supabase_headers()
    if creds is None:
        return None
    url, headers = creds
    response = httpx.get(
        f"{url}/rest/v1/pipeline_runs",
        headers=headers,
        params=[("select", "*"), ("order", "started_at.desc"), ("limit", "1")],
        timeout=20.0,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        return None
    return rows[0]


def default_heartbeat(run_id: str) -> None:
    logger.info("clinic_supply_pipeline_heartbeat run_id=%s", run_id)


_extract: ExtractFn = extract_from_supabase
_load: LoadFn = load_to_supabase
_insert_run: InsertRunFn = insert_run_supabase
_update_run: UpdateRunFn = update_run_supabase
_list_kpis: Callable[[str | None], list[dict[str, Any]]] = list_kpi_rows_supabase
_latest_run: Callable[[], dict[str, Any] | None] = latest_run_supabase
_heartbeat: HeartbeatFn = default_heartbeat


def set_extract(fn: ExtractFn | None) -> None:
    global _extract
    _extract = fn or extract_from_supabase


def set_load(fn: LoadFn | None) -> None:
    global _load
    _load = fn or load_to_supabase


def set_run_log(insert_fn: InsertRunFn | None, update_fn: UpdateRunFn | None) -> None:
    global _insert_run, _update_run
    _insert_run = insert_fn or insert_run_supabase
    _update_run = update_fn or update_run_supabase


def set_readers(
    list_fn: Callable[[str | None], list[dict[str, Any]]] | None,
    latest_fn: Callable[[], dict[str, Any] | None] | None,
) -> None:
    global _list_kpis, _latest_run
    _list_kpis = list_fn or list_kpi_rows_supabase
    _latest_run = latest_fn or latest_run_supabase


def set_heartbeat(fn: HeartbeatFn | None) -> None:
    global _heartbeat
    _heartbeat = fn or default_heartbeat


def list_clinic_month_rows(month_start: str | None) -> list[dict[str, Any]]:
    return _list_kpis(month_start)


def latest_pipeline_run() -> dict[str, Any] | None:
    return _latest_run()


def reset_pipeline_hooks() -> None:
    set_extract(None)
    set_load(None)
    set_run_log(None, None)
    set_readers(None, None)
    set_heartbeat(None)


def _transform_cache_key(_context: Any, parameters: dict[str, Any]) -> str:
    events = parameters.get("events") or []
    ids = sorted(_event_id(item, _tags(item)) or "" for item in events)
    window = parameters.get("window") or {}
    return f"clinic-kpi:{window.get('start')}:{window.get('end')}:{','.join(ids)}"


@task(retries=3, retry_delay_seconds=5)
def extract_clinic_supply_events(window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    # PostgREST blips: 3 tries, 5s apart is enough for a monthly job without hammering.
    return _extract(window_start, window_end)


@task(cache_key_fn=_transform_cache_key, cache_expiration=timedelta(hours=1))
def transform_clinic_month_kpis_task(
    events: list[dict[str, Any]],
    window: dict[str, str],
) -> dict[str, Any]:
    """Cache 1h on window_start, window_end, and sorted eventId list."""
    return transform_clinic_month_kpis(events, window)


@task(retries=3, retry_delay_seconds=5)
def load_monthly_clinic_supply_performance(rows: list[dict[str, Any]]) -> int:
    # Same PostgREST retry policy as extract.
    return _load(rows)


@task
def emit_clinic_supply_pipeline_heartbeat(run_id: str) -> None:
    _heartbeat(run_id)


def _run_optional_heartbeat(heartbeat_stage: Callable[[str], Any], run_id: str) -> None:
    try:
        result = heartbeat_stage(run_id)
    except Exception:
        logger.warning("optional heartbeat failed run_id=%s", run_id)
        return
    is_failed = getattr(result, "is_failed", None)
    if callable(is_failed) and is_failed():
        logger.warning("optional heartbeat failed run_id=%s", run_id)


def _coordinate_clinic_supply_run(
    month_start: date | None,
    extract_stage: ExtractFn,
    transform_stage: Callable[[list[dict[str, Any]], dict[str, str]], dict[str, Any]],
    load_stage: LoadFn,
    heartbeat_stage: Callable[[str], Any],
) -> dict[str, Any]:
    if not pipeline_lock.acquire(blocking=False):
        raise PipelineBusyError()
    run_id = str(uuid4())
    started = _utcnow()
    target = month_start or previous_utc_month()
    window_start, window_end = window_for_month(target)
    window = {"start": window_start.isoformat(), "end": window_end.isoformat()}
    record = {
        "run_id": run_id,
        "started_at": started.isoformat(),
        "finished_at": None,
        "status": "running",
        "records_processed": 0,
        "error": None,
        "window_start": window["start"],
        "window_end": window["end"],
        "events_extracted": 0,
        "events_quarantined": 0,
    }
    try:
        _insert_run(record)
        events = extract_stage(window_start, window_end)
        transformed = transform_stage(events, window)
        stored = load_stage(transformed["rows"])
        _run_optional_heartbeat(heartbeat_stage, run_id)
        finished = _utcnow()
        record.update(
            {
                "finished_at": finished.isoformat(),
                "status": "completed",
                "records_processed": stored,
                "events_extracted": transformed["events_extracted"],
                "events_quarantined": transformed["events_quarantined"],
            }
        )
        _update_run(run_id, record)
        return record
    except PipelineBusyError:
        raise
    except Exception as exc:
        finished = _utcnow()
        record.update(
            {
                "finished_at": finished.isoformat(),
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        try:
            _update_run(run_id, record)
        except Exception:
            logger.exception("failed to persist pipeline_runs failure row")
        raise
    finally:
        if pipeline_lock.locked():
            pipeline_lock.release()


def execute_monthly_clinic_supply_performance(month_start: date | None = None) -> dict[str, Any]:
    """Run extract/transform/load without starting a Prefect API server."""
    return _coordinate_clinic_supply_run(
        month_start,
        extract_clinic_supply_events.fn,
        transform_clinic_month_kpis_task.fn,
        load_monthly_clinic_supply_performance.fn,
        emit_clinic_supply_pipeline_heartbeat.fn,
    )


@flow(name="extract_clinic_supply_events")
def extract_clinic_supply_events_flow(
    window_start: datetime, window_end: datetime
) -> list[dict[str, Any]]:
    return extract_clinic_supply_events(window_start, window_end)


@flow(name="transform_clinic_month_kpis")
def transform_clinic_month_kpis_flow(
    events: list[dict[str, Any]],
    window: dict[str, str],
) -> dict[str, Any]:
    return transform_clinic_month_kpis_task(events, window)


@flow(name="load_monthly_clinic_supply_performance")
def load_monthly_clinic_supply_performance_flow(rows: list[dict[str, Any]]) -> int:
    return load_monthly_clinic_supply_performance(rows)


@flow(name="emit_clinic_supply_pipeline_heartbeat")
def emit_clinic_supply_pipeline_heartbeat_flow(run_id: str) -> None:
    emit_clinic_supply_pipeline_heartbeat(run_id)


def _heartbeat_subflow_state(run_id: str) -> Any:
    return emit_clinic_supply_pipeline_heartbeat_flow(run_id, return_state=True)


@flow(name="monthly_clinic_supply_performance")
def monthly_clinic_supply_performance(month_start: date | None = None) -> dict[str, Any]:
    """Prefect coordinator: three ETL subflows plus optional heartbeat. HTTP/CLI use execute_."""
    return _coordinate_clinic_supply_run(
        month_start,
        extract_clinic_supply_events_flow,
        transform_clinic_month_kpis_flow,
        load_monthly_clinic_supply_performance_flow,
        _heartbeat_subflow_state,
    )


if __name__ == "__main__":
    result = execute_monthly_clinic_supply_performance()
    print(result)
