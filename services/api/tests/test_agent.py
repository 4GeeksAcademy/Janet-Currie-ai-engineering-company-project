"""Contract tests for POST /agent/query. The model and Qdrant stay faked."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent import graph as agent_graph
from pipelines.rag import GenerationUnavailableError, RetrievalUnavailableError
from process.rag import QUESTION_MAX_CHARS, ConfigurationError
from tests.helpers import auth_header, client


def _ready_settings(**_kwargs):
    return SimpleNamespace(k=5, min_score=0.4)


def test_signed_in_question_returns_answer_and_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)
    monkeypatch.setattr(
        agent_graph,
        "retrieve",
        lambda *_args, **_kwargs: [
            {"source_document": "healthcore-insurance-coverage.en.md", "text": "Georgia"}
        ],
    )
    monkeypatch.setattr(
        agent_graph,
        "generate_answer",
        lambda *_args, **_kwargs: "Georgia clinics do not accept Medicaid.",
    )
    response = client.post(
        "/agent/query",
        json={"question": "Can a patient use Medicaid at a Georgia clinic?"},
        headers=auth_header(email="agent-ok@healthcore.example"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Georgia clinics do not accept Medicaid."
    assert body["run_id"]
    assert set(body) == {"answer", "run_id"}
    forbidden = {"context", "chunks", "score", "vector", "prompt", "checkpoint"}
    assert forbidden.isdisjoint(body)


def test_empty_too_long_and_extra_fields_are_rejected() -> None:
    headers = auth_header(email="agent-blank@healthcore.example")
    empty = client.post("/agent/query", json={"question": "   "}, headers=headers)
    assert empty.status_code == 422
    huge = client.post(
        "/agent/query",
        json={"question": "a" * (QUESTION_MAX_CHARS + 1)},
        headers=headers,
    )
    assert huge.status_code == 422
    extra = client.post(
        "/agent/query",
        json={"question": "Do Georgia clinics accept Medicaid?", "chunks": []},
        headers=headers,
    )
    assert extra.status_code == 422


def test_signed_out_request_is_rejected() -> None:
    response = client.post(
        "/agent/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
    )
    assert response.status_code == 401


def test_search_failure_stays_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = auth_header(email="agent-down@healthcore.example")
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)

    def search_down(*_args, **_kwargs):
        raise RetrievalUnavailableError("Traceback (most recent call last): qdrant secret")

    monkeypatch.setattr(agent_graph, "retrieve", search_down)
    response = client.post(
        "/agent/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
        headers=headers,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == agent_graph.SEARCH_UNAVAILABLE
    lowered = response.text.lower()
    assert "traceback" not in lowered
    assert "qdrant" not in lowered
    assert "secret" not in lowered
    assert "chunks" not in response.json()
    assert "score" not in response.json()


def test_writer_and_settings_failures_use_their_own_sentences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = auth_header(email="agent-writer@healthcore.example")
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)
    monkeypatch.setattr(
        agent_graph,
        "retrieve",
        lambda *_args, **_kwargs: [{"source_document": "policy.md", "text": "A fact."}],
    )

    def writer_down(*_args, **_kwargs):
        raise GenerationUnavailableError("model timeout at https://models.example")

    monkeypatch.setattr(agent_graph, "generate_answer", writer_down)
    writer_response = client.post(
        "/agent/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
        headers=headers,
    )
    assert writer_response.status_code == 503
    assert writer_response.json()["detail"] == agent_graph.ANSWER_UNAVAILABLE
    assert "https" not in writer_response.text.lower()

    def missing_score(**_kwargs):
        raise ConfigurationError("RAG_MIN_SCORE is not set")

    monkeypatch.setattr(agent_graph, "load_settings", missing_score)
    config_response = client.post(
        "/agent/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
        headers=headers,
    )
    assert config_response.status_code == 503
    assert config_response.json()["detail"] == agent_graph.NOT_CONFIGURED
    assert "RAG_MIN_SCORE" not in config_response.text
