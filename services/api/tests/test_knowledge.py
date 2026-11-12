"""Contract tests for POST /knowledge/query. The model and Qdrant stay faked."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.routers import knowledge
from pipelines.rag import GenerationUnavailableError, RetrievalUnavailableError
from process.rag import QUESTION_MAX_CHARS, ConfigurationError
from tests.helpers import auth_header, client


def test_signed_in_question_returns_only_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(knowledge, "query", lambda _question: "Private-pay patients may owe 50 USD.")
    response = client.post(
        "/knowledge/query",
        json={"question": "Is there a charge for cancelling 12 hours in advance?"},
        headers=auth_header(),
    )
    assert response.status_code == 200
    assert response.json() == {"answer": "Private-pay patients may owe 50 USD."}
    forbidden = {"context", "chunks", "score", "vector", "prompt"}
    assert forbidden.isdisjoint(response.json())


def test_empty_and_huge_questions_are_rejected() -> None:
    headers = auth_header(email="blank@healthcore.example")
    empty = client.post("/knowledge/query", json={"question": "   "}, headers=headers)
    assert empty.status_code == 422
    huge = client.post(
        "/knowledge/query",
        json={"question": "a" * (QUESTION_MAX_CHARS + 1)},
        headers=headers,
    )
    assert huge.status_code == 422
    missing = client.post("/knowledge/query", json={}, headers=headers)
    assert missing.status_code == 422


def test_signed_out_request_is_rejected() -> None:
    response = client.post("/knowledge/query", json={"question": "Do we accept Medicaid?"})
    assert response.status_code == 401


def test_search_and_answer_failures_stay_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = auth_header(email="outage@healthcore.example")

    def search_down(_question: str) -> str:
        raise RetrievalUnavailableError("http://qdrant:6333 secret")

    monkeypatch.setattr(knowledge, "query", search_down)
    search_response = client.post(
        "/knowledge/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
        headers=headers,
    )
    assert search_response.status_code == 503
    search_body = search_response.text.lower()
    assert "qdrant" not in search_body
    assert "http" not in search_body
    assert "secret" not in search_body

    def writer_down(_question: str) -> str:
        raise GenerationUnavailableError("model timeout at https://models.example")

    monkeypatch.setattr(knowledge, "query", writer_down)
    writer_response = client.post(
        "/knowledge/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
        headers=headers,
    )
    assert writer_response.status_code == 503
    assert writer_response.json()["detail"] != search_response.json()["detail"]
    assert "https" not in writer_response.text.lower()


def test_missing_configuration_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = auth_header(email="config@healthcore.example")

    def unconfigured(_question: str) -> str:
        raise ConfigurationError("EMBEDDING_MODEL_ID is missing")

    monkeypatch.setattr(knowledge, "query", unconfigured)
    response = client.post(
        "/knowledge/query",
        json={"question": "What should a new patient bring?"},
        headers=headers,
    )
    assert response.status_code == 503
    assert "EMBEDDING_MODEL_ID" not in response.text
    assert response.json()["detail"] == "The knowledge assistant is not configured. Please try again later."


def test_router_does_not_search_or_call_a_model() -> None:
    source = Path(knowledge.__file__).read_text(encoding="utf-8")
    assert "query_points" not in source
    assert "chat/completions" not in source
    assert "/embeddings" not in source
