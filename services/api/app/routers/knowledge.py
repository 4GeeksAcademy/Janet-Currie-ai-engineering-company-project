"""Signed-in door to the knowledge helper. The search and the writing live in data/pipelines."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.security import get_current_user
from pipelines.rag import (
    EmptyQueryError,
    GenerationUnavailableError,
    RetrievalUnavailableError,
    query,
)
from process.rag import QUESTION_MAX_CHARS, ConfigurationError, EmbeddingError

logger = logging.getLogger("healthcore.knowledge")

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(get_current_user)],
)


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)

    @field_validator("question")
    @classmethod
    def question_has_words(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Question is required")
        return cleaned


class KnowledgeAnswer(BaseModel):
    answer: str


@router.post("/query", response_model=KnowledgeAnswer)
def ask_knowledge(body: KnowledgeQuery) -> KnowledgeAnswer:
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    try:
        answer = query(body.question)
    except EmptyQueryError:
        logger.info("knowledge_http request_id=%s error_category=validation", request_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question is required",
        ) from None
    except RetrievalUnavailableError:
        logger.info("knowledge_http request_id=%s error_category=qdrant", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge search is unavailable. Please try again.",
        ) from None
    except (GenerationUnavailableError, EmbeddingError):
        logger.info("knowledge_http request_id=%s error_category=generation", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The answer service is unavailable. Please try again.",
        ) from None
    except ConfigurationError:
        logger.info("knowledge_http request_id=%s error_category=configuration", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge assistant is not configured. Please try again later.",
        ) from None
    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "knowledge_http request_id=%s duration_ms=%s error_category=none",
        request_id,
        duration_ms,
    )
    return KnowledgeAnswer(answer=answer)
