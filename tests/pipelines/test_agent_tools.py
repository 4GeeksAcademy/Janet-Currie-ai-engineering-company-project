"""Incident routing for the support-agent map. Search and writing stay faked."""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app import store
from app.agent import graph as agent_graph
from app.agent.graph import compile_agent, run_agent
from app.agent.incidents import INCIDENT_LOOKUP_TIMEOUT_SECONDS
from app.agent.trace import MemoryTraceStore

REPO_ROOT = Path(__file__).resolve().parents[2]
INCIDENT_TRACE = REPO_ROOT / "data" / "eval" / "agent-incident-trace-example.json"
RAG_TRACE = REPO_ROOT / "data" / "eval" / "agent-rag-trace-example.json"
CLOSED_ROW = {
    "incident_id": "HC-000006",
    "date": "2026-01-15",
    "clinic_id": "UK-MAN-01",
    "country": "UK",
    "category": "CLINICAL_CARE",
    "status": "CLOSED",
    "patient_id": "PAT-900006",
    "description": "Closed without a satisfaction score recorded.",
}
POLICY_ANSWER = "Escalate a stalled referral to Marcus Reid after five business days."
STAFF_TOKEN = "staff-test-token"
SAFE_ROW = {key: value for key, value in CLOSED_ROW.items() if key in {"incident_id", "date", "clinic_id", "country", "category", "status"}}


def _summary() -> SimpleNamespace:
    return SimpleNamespace(source_file="incidents.csv")


def _ready_settings(**_kwargs):
    return SimpleNamespace(k=5, min_score=0.4)


class _IncidentTool:
    def __init__(self, handler):
        self.name = "get_incident_status"
        self.handler = handler

    async def ainvoke(self, args):
        return self.handler(args)


class DoorClient:
    def __init__(self, connections):
        self.connections = connections
        DoorClient.calls.append(connections)

    calls: list = []
    handler = staticmethod(lambda _args: {"outcome": "not_found", "status": None})

    async def get_tools(self, server_name=None):
        return [_IncidentTool(DoorClient.handler)]


def _use_door(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    DoorClient.calls = []
    DoorClient.handler = staticmethod(handler)
    monkeypatch.setattr("app.agent.incidents.MultiServerMCPClient", DoorClient)


def _run(question: str, run_id: str):
    trace = MemoryTraceStore()
    graph = compile_agent(InMemorySaver())
    result = run_agent(
        graph,
        question,
        run_id=run_id,
        trace_store=trace,
        staff_token=STAFF_TOKEN,
    )
    return result, trace


def setup_function() -> None:
    store.clear()


def teardown_function() -> None:
    store.clear()


def test_saved_rows_drop_patient_id() -> None:
    store.save_analysis(_summary(), [CLOSED_ROW])
    saved = store.get_incident("HC-000006")
    assert saved is not None
    assert saved["status"] == "CLOSED"
    assert "patient_id" not in saved
    assert "PAT-" not in json.dumps(saved)
    assert "description" not in saved


def test_incident_question_reads_the_door_once(monkeypatch: pytest.MonkeyPatch) -> None:
    store.save_analysis(_summary(), [CLOSED_ROW])

    def found(_args):
        return {"outcome": "found", **SAFE_ROW}

    _use_door(monkeypatch, found)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("an incident question must not search the papers")

    monkeypatch.setattr(agent_graph, "retrieve", forbidden)
    monkeypatch.setattr(agent_graph, "generate_answer", forbidden)
    result, trace = _run("What is the status of incident HC-000006?", "incident-status")
    events = trace.list("incident-status")
    assert len(DoorClient.calls) == 1
    assert DoorClient.calls[0]["healthcore"]["headers"]["Authorization"] == f"Bearer {STAFF_TOKEN}"
    assert result["status"] == "grounded"
    assert "HC-000006" in result["answer"]
    assert "CLOSED" in result["answer"]
    assert [event["node"] for event in events] == ["validate", "route", "lookup"]
    assert "retrieve" not in [event["node"] for event in events]
    assert events[-1]["tool_outcome"] == "found"
    assert events[-1]["incident_id"] == "HC-000006"
    assert "PAT-" not in result["answer"]
    assert STAFF_TOKEN not in json.dumps(events)
    assert STAFF_TOKEN not in result["answer"]
    INCIDENT_TRACE.write_text(
        json.dumps({"run_id": "incident-status", "events": events}, indent=2) + "\n"
    )


def test_policy_question_does_not_read_incidents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a policy question must not call the tool door")

    monkeypatch.setattr("app.agent.incidents.MultiServerMCPClient", forbidden)
    monkeypatch.setattr(
        agent_graph,
        "retrieve",
        lambda *_args, **_kwargs: [
            {"source_document": "healthcore-referral-process.en.md", "text": "Five business days."}
        ],
    )
    monkeypatch.setattr(agent_graph, "generate_answer", lambda *_args, **_kwargs: POLICY_ANSWER)
    result, trace = _run("What is our referral escalation rule?", "policy-rule")
    events = trace.list("policy-rule")
    assert result["answer"] == POLICY_ANSWER
    assert [event["node"] for event in events] == ["validate", "route", "retrieve", "generate"]
    assert events[1]["route"] == "rag"
    assert "lookup" not in [event["node"] for event in events]
    RAG_TRACE.write_text(json.dumps({"run_id": "policy-rule", "events": events}, indent=2) + "\n")


def test_missing_timeout_and_bad_id_stay_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("these questions must not search the papers")

    monkeypatch.setattr(agent_graph, "retrieve", forbidden)
    monkeypatch.setattr(agent_graph, "generate_answer", forbidden)
    _use_door(monkeypatch, lambda _args: {"outcome": "not_found", "status": None})
    missing, missing_trace = _run("What is the status of incident HC-999999?", "missing-incident")
    assert "could not be confirmed" in missing["answer"].lower()
    assert "CLOSED" not in missing["answer"]
    assert missing_trace.list("missing-incident")[-1]["tool_outcome"] == "not_found"

    def slow(_args):
        time.sleep(0.3)
        return {"outcome": "found", **SAFE_ROW}

    _use_door(monkeypatch, slow)
    monkeypatch.setattr("app.agent.incidents.INCIDENT_LOOKUP_TIMEOUT_SECONDS", 0.05)
    assert INCIDENT_LOOKUP_TIMEOUT_SECONDS == 3
    timed_out, _trace = _run("What is the status of incident HC-000006?", "slow-incident")
    assert timed_out["answer"] == "The current status could not be confirmed."
    assert "CLOSED" not in timed_out["answer"]

    def explode(*_args, **_kwargs):
        raise AssertionError("ticket 482 must not call the tool door")

    monkeypatch.setattr("app.agent.incidents.MultiServerMCPClient", explode)
    bad, bad_trace = _run("What is the status of ticket 482?", "bad-ticket")
    assert bad["status"] == "invalid"
    assert "HC-000006" in bad["answer"]
    assert [event["node"] for event in bad_trace.list("bad-ticket")] == ["validate", "route"]


def test_both_paths_keep_the_policy_half_when_the_incident_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)
    order: list[str] = []

    def retrieve(*_args, **_kwargs):
        order.append("retrieve")
        return [{"source_document": "healthcore-referral-process.en.md", "text": "Five business days."}]

    def generate(*_args, **_kwargs):
        order.append("generate")
        return POLICY_ANSWER

    def missing(_args):
        order.append("lookup")
        return {"outcome": "not_found", "status": None}

    monkeypatch.setattr(agent_graph, "retrieve", retrieve)
    monkeypatch.setattr(agent_graph, "generate_answer", generate)
    _use_door(monkeypatch, missing)
    result, trace = _run(
        "What is our referral escalation rule, and what is the status of HC-000006?",
        "both-partial",
    )
    nodes = [event["node"] for event in trace.list("both-partial")]
    assert nodes.index("lookup") < nodes.index("retrieve")
    assert order[:2] == ["lookup", "retrieve"]
    assert POLICY_ANSWER in result["answer"]
    assert "could not be confirmed" in result["answer"].lower()
    assert "CLOSED" not in result["answer"]


def test_two_runs_do_not_share_incident_traces(monkeypatch: pytest.MonkeyPatch) -> None:
    store.save_analysis(_summary(), [CLOSED_ROW])
    _use_door(monkeypatch, lambda _args: {"outcome": "found", **SAFE_ROW})
    monkeypatch.setattr(agent_graph, "load_settings", _ready_settings)
    monkeypatch.setattr(agent_graph, "retrieve", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(agent_graph, "generate_answer", lambda *_args, **_kwargs: "unused")
    trace = MemoryTraceStore()
    graph = compile_agent(InMemorySaver())
    run_agent(
        graph,
        "What is the status of incident HC-000006?",
        run_id="run-incident",
        trace_store=trace,
        staff_token=STAFF_TOKEN,
    )
    run_agent(
        graph,
        "What is our referral escalation rule?",
        run_id="run-policy",
        trace_store=trace,
        staff_token=STAFF_TOKEN,
    )
    first = trace.list("run-incident")
    second = trace.list("run-policy")
    assert {event["run_id"] for event in first} == {"run-incident"}
    assert {event["run_id"] for event in second} == {"run-policy"}
    blob = json.dumps({"first": first, "second": second, "answer": graph.get_state({"configurable": {"thread_id": "run-incident"}}).values["answer"]})
    assert "patient_id" not in blob
    assert "PAT-" not in blob
    assert STAFF_TOKEN not in blob
