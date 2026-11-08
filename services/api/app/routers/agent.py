"""Signed-in door to the support-agent map. This file does not search or write."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.graph import (
    ANSWER_UNAVAILABLE,
    NOT_CONFIGURED,
    QUESTION_REQUIRED,
    SEARCH_UNAVAILABLE,
    run_agent,
)
from app.auth.security import get_current_user, oauth2_scheme
from process.rag import QUESTION_MAX_CHARS

logger = logging.getLogger("healthcore.agent")

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(get_current_user)],
)


class AgentQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)

    @field_validator("question")
    @classmethod
    def question_has_words(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError(QUESTION_REQUIRED)
        return cleaned


class AgentAnswer(BaseModel):
    answer: str
    run_id: str


@router.post("/query", response_model=AgentAnswer)
def ask_agent(
    request: Request,
    body: AgentQuery,
    token: str = Depends(oauth2_scheme),
) -> AgentAnswer:
    run_id = uuid.uuid4().hex
    started = time.perf_counter()
    graph = getattr(request.app.state, "agent_graph", None)
    trace_store = getattr(request.app.state, "agent_traces", None)
    if graph is None or trace_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=NOT_CONFIGURED,
        )
    try:
        result = run_agent(
            graph,
            body.question,
            run_id=run_id,
            trace_store=trace_store,
            staff_token=token,
        )
    except Exception:
        logger.info("agent_http run_id=%s error_category=unhandled", run_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SEARCH_UNAVAILABLE,
        ) from None
    outcome = result.get("status")
    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "agent_http run_id=%s status=%s duration_ms=%s",
        run_id,
        outcome,
        duration_ms,
    )
    if outcome == "invalid":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.get("answer") or QUESTION_REQUIRED,
        )
    if outcome == "failed":
        detail = result.get("answer") or SEARCH_UNAVAILABLE
        if detail not in {SEARCH_UNAVAILABLE, ANSWER_UNAVAILABLE, NOT_CONFIGURED}:
            detail = SEARCH_UNAVAILABLE
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    return AgentAnswer(answer=result.get("answer") or "", run_id=run_id)
