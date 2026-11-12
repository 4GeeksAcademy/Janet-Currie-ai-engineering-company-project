"""The support-agent map, with the search and the writing model faked."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent import graph as agent_graph
from app.agent.graph import NO_MATCH_ANSWER, compile_agent, run_agent
from app.agent.trace import MemoryTraceStore
from pipelines.rag import RetrievalUnavailableError
from process.rag import QUESTION_MAX_CHARS

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACE_EXAMPLE = REPO_ROOT / "data" / "eval" / "agent-trace-example.json"
GEORGIA_QUESTION = "Can a patient use Medicaid at a Georgia clinic?"
GEORGIA_PASSAGE = {
    "company": "HealthCore",
    "source_document": "healthcore-insurance-coverage.en.md",
    "section": "United States",
    "language": "en",
    "chunk_index": 0,
    "text": "Medicaid is not currently accepted at Georgia clinics.",
}
GEORGIA_ANSWER = "Georgia clinics do not accept Medicaid."


def _ready_settings(**_kwargs):
    return SimpleNamespace(k=5, min_score=0.4)


def _run(question: str, run_id: str, store: MemoryTraceStore):
    graph = compile_agent(InMemorySaver())
    result = run_agent(graph, question, run_id=run_id, trace_store=store)
    return graph, result


def test_georgia_medicaid_searches_once_then_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"retrieve": 0, "generate": 0}
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)

    def fake_retrieve(question: str, *, k: int, min_score: float):
        calls["retrieve"] += 1
        assert question == GEORGIA_QUESTION
        assert k == 5
        assert min_score == 0.4
        return [dict(GEORGIA_PASSAGE)]

    def fake_generate(question: str, context: list[dict]) -> str:
        calls["generate"] += 1
        assert question == GEORGIA_QUESTION
        assert context == [GEORGIA_PASSAGE]
        return GEORGIA_ANSWER

    monkeypatch.setattr(agent_graph, "retrieve", fake_retrieve)
    monkeypatch.setattr(agent_graph, "generate_answer", fake_generate)
    store = MemoryTraceStore()
    graph, result = _run(GEORGIA_QUESTION, "georgia-medicaid", store)

    assert calls == {"retrieve": 1, "generate": 1}
    assert result["status"] == "grounded"
    assert "Georgia clinics do not accept Medicaid" in result["answer"]
    events = store.list("georgia-medicaid")
    assert [event["node"] for event in events] == ["validate", "retrieve", "generate"]
    assert events[1]["passage_count"] == 1
    assert events[1]["source_documents"] == ["healthcore-insurance-coverage.en.md"]
    assert "question" not in events[0]
    snapshot = graph.get_state({"configurable": {"thread_id": "georgia-medicaid"}})
    assert snapshot.values["answer"] == GEORGIA_ANSWER
    assert snapshot.config["configurable"]["thread_id"] == "georgia-medicaid"
    assert snapshot.config["configurable"]["checkpoint_id"]
    TRACE_EXAMPLE.write_text(json.dumps({"run_id": "georgia-medicaid", "events": events}, indent=2) + "\n")
    saved = json.loads(TRACE_EXAMPLE.read_text())
    assert saved["events"][2]["answer"] == GEORGIA_ANSWER
    assert GEORGIA_QUESTION not in TRACE_EXAMPLE.read_text()


def test_blank_question_does_not_search_or_write(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("blank questions must not search or write")

    monkeypatch.setattr(agent_graph, "retrieve", forbidden)
    monkeypatch.setattr(agent_graph, "generate_answer", forbidden)
    monkeypatch.setattr(agent_graph, "load_settings", forbidden)
    store = MemoryTraceStore()
    _graph, result = _run("   \n\t", "blank-question", store)
    assert result["status"] == "invalid"
    assert result["answer"] == "Question is required"
    events = store.list("blank-question")
    assert [event["node"] for event in events] == ["validate"]
    assert events[-1]["status"] == "invalid"


def test_too_long_question_stops_before_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("a too-long question must not search")

    monkeypatch.setattr(agent_graph, "retrieve", forbidden)
    monkeypatch.setattr(agent_graph, "generate_answer", forbidden)
    store = MemoryTraceStore()
    _graph, result = _run("a" * (QUESTION_MAX_CHARS + 1), "too-long", store)
    assert result["status"] == "invalid"
    assert store.list("too-long")[-1]["node"] == "validate"


def test_empty_search_uses_the_fixed_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)
    monkeypatch.setattr(agent_graph, "retrieve", lambda *_args, **_kwargs: [])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("an empty search must not call the writing model")

    monkeypatch.setattr(agent_graph, "generate_answer", forbidden)
    store = MemoryTraceStore()
    _graph, result = _run("What is the capital of France?", "no-match", store)
    assert result["status"] == "no_context"
    assert result["answer"] == NO_MATCH_ANSWER
    assert [event["node"] for event in store.list("no-match")] == [
        "validate",
        "retrieve",
        "no_match",
    ]


def test_two_runs_do_not_share_traces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)
    monkeypatch.setattr(agent_graph, "retrieve", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(agent_graph, "generate_answer", lambda *_args, **_kwargs: "unused")
    store = MemoryTraceStore()
    graph = compile_agent(InMemorySaver())
    run_agent(graph, "First question about parking?", run_id="run-a", trace_store=store)
    run_agent(graph, "Second question about parking?", run_id="run-b", trace_store=store)
    first = store.list("run-a")
    second = store.list("run-b")
    assert first and second
    assert {event["run_id"] for event in first} == {"run-a"}
    assert {event["run_id"] for event in second} == {"run-b"}
    assert graph.get_state({"configurable": {"thread_id": "run-a"}}).values["answer"] == NO_MATCH_ANSWER
    assert graph.get_state({"configurable": {"thread_id": "run-b"}}).config["configurable"]["thread_id"] == "run-b"


def test_search_failure_becomes_a_safe_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)

    def explode(*_args, **_kwargs):
        raise RetrievalUnavailableError("Traceback (most recent call last): qdrant secret")

    monkeypatch.setattr(agent_graph, "retrieve", explode)
    store = MemoryTraceStore()
    _graph, result = _run("Do Georgia clinics accept Medicaid?", "search-down", store)
    assert result["status"] == "failed"
    assert result["answer"] == agent_graph.SEARCH_UNAVAILABLE
    assert "Traceback" not in result["answer"]
    assert store.list("search-down")[-1]["status"] == "failed"

    from tests.helpers import auth_header, client

    response = client.post(
        "/agent/query",
        json={"question": "Do Georgia clinics accept Medicaid?"},
        headers=auth_header(email="agent-graph-down@healthcore.example"),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == agent_graph.SEARCH_UNAVAILABLE
    assert "traceback" not in response.text.lower()
    assert "qdrant" not in response.text.lower()
