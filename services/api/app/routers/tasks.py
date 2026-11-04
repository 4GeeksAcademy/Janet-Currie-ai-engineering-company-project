"""JWT task-status polling (DEV-55)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.security import get_current_user
from app.celery_app import BrokerUnavailableError
from app.reporting.schemas import TaskStatusResponse
from app.tasks.status import InvalidTaskIdError, task_status

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str) -> TaskStatusResponse:
    try:
        return task_status(task_id)
    except InvalidTaskIdError:
        raise HTTPException(
            status_code=422,
            detail="task_id is malformed",
        ) from None
    except BrokerUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue is unavailable. Please try again.",
        ) from None
