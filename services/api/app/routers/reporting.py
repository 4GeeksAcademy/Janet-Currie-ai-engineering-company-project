"""Authenticated reporting API. ETL is invoked from data/pipelines only."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.security import get_current_user
from app.reporting.queries import clinic_month_report, latest_run
from app.reporting.schemas import (
    ClinicSupplyKpi,
    MonthlyClinicSupplyPerformanceResponse,
    PipelineRunRequest,
    PipelineRunResponse,
)
from pipelines.pipeline import PipelineBusyError, execute_monthly_clinic_supply_performance

router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
    dependencies=[Depends(get_current_user)],
)


def _run_response(row: dict) -> PipelineRunResponse:
    return PipelineRunResponse(
        run_id=str(row["run_id"]),
        status=str(row["status"]),
        started_at=str(row["started_at"]),
        finished_at=None if row.get("finished_at") is None else str(row["finished_at"]),
        records_processed=int(row.get("records_processed") or 0),
        events_extracted=int(row.get("events_extracted") or 0),
        events_quarantined=int(row.get("events_quarantined") or 0),
        window_start=str(row["window_start"]),
        window_end=str(row["window_end"]),
        error=row.get("error"),
    )


@router.get(
    "/monthly-clinic-supply-performance",
    response_model=MonthlyClinicSupplyPerformanceResponse,
)
def monthly_clinic_supply_performance_report(
    month_start: date | None = Query(default=None),
) -> MonthlyClinicSupplyPerformanceResponse:
    if month_start is not None and month_start.day != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month_start must be the first day of a month",
        )
    resolved, rows = clinic_month_report(month_start)
    clinics = [
        ClinicSupplyKpi(
            clinic_id=str(row["clinic_id"]),
            country=str(row["country"]),
            total_supply_cost=float(row["total_supply_cost"]),
            supply_consumption_count=int(row["supply_consumption_count"]),
            critical_stockout_count=int(row["critical_stockout_count"]),
            expiry_risk_count=int(row["expiry_risk_count"]),
            currency=str(row["currency"]),
        )
        for row in rows
    ]
    return MonthlyClinicSupplyPerformanceResponse(
        month_start=date.fromisoformat(resolved) if resolved else None,
        clinics=clinics,
    )


@router.get("/pipeline-runs/latest", response_model=PipelineRunResponse)
def pipeline_runs_latest() -> PipelineRunResponse:
    row = latest_run()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pipeline runs")
    return _run_response(row)


@router.post("/pipeline-runs", response_model=PipelineRunResponse)
def trigger_pipeline_run(body: PipelineRunRequest = PipelineRunRequest()) -> PipelineRunResponse:
    requested = body.month_start
    if requested is not None and requested.day != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month_start must be the first day of a month",
        )
    try:
        record = execute_monthly_clinic_supply_performance(requested)
    except PipelineBusyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pipeline run is already in progress",
        ) from None
    return _run_response(record)
