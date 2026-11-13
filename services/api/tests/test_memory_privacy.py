"""Privacy gate, blocked audits, and durable copies of staff text."""

from __future__ import annotations

import logging

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agent.checkpoint import DurableSafeSaver
from app.agent.graph import compile_agent, run_agent
from app.agent.privacy import validate_memory_text
from app.agent.trace import MemoryTraceStore

MANCHESTER = (
    "At the Manchester clinic, internal referrals now go through the coordinator "
    "before the specialist; that changed last quarter."
)
MONDAY = "The referral system tends to fail on Monday mornings because of the overnight batch job."
VACANCIES = (
    "The signed-in user wants the weekly vacancies report broken down by role "
    "rather than only by clinic."
)


def test_operational_text_is_allowed() -> None:
    for text in (MANCHESTER, MONDAY, VACANCIES, "Incident HC-000006 is an operational id.", "Clinic UK-MAN-01 is in the UK."):
        result = validate_memory_text(text)
        assert result.allowed, text
        assert result.reason_codes == ()


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("Remember that patient Alex Example cancelled.", "patient_identifier"),
        ("Store MRN ZX-0000 in the memory.", "mrn"),
        ("Date of birth 1990-01-01 should be kept.", "date_of_birth"),
        ("Diagnosis: example condition.", "clinical_content"),
        ("Insurance number INS-000 belongs on the file.", "insurance_identifier"),
        (
            "Alex Example had a visit on 1990-01-01 at clinic UK-MAN-01.",
            "reidentification",
        ),
    ],
)
def test_phi_patterns_are_refused(text: str, reason: str) -> None:
    result = validate_memory_text(text)
    assert not result.allowed
    assert reason in result.reason_codes
    assert text not in repr(result)


def test_validator_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.privacy._PATIENT_NAME", None)
    result = validate_memory_text("The front desk opens at 8.")
    assert not result.allowed
    assert result.reason_codes == ("validator_error",)


def test_sqlite_checkpoint_omits_question_and_answer(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = "SENTINEL_QUESTION_TEXT_SHOULD_NOT_PERSIST"
    answer = "SENTINEL_ANSWER_TEXT_SHOULD_NOT_PERSIST"
    monkeypatch.setattr("app.agent.graph.load_settings", lambda **_kwargs: __import__("types").SimpleNamespace(k=5, min_score=0.4))
    monkeypatch.setattr("app.agent.graph.retrieve", lambda *_args, **_kwargs: [{"source_document": "ops.md", "text": "hours"}])
    monkeypatch.setattr("app.agent.graph.generate_answer", lambda *_args, **_kwargs: answer)
    monkeypatch.setattr("app.agent.graph.propose_memory", lambda *_args, **_kwargs: None)
    path = tmp_path / "checkpoints.sqlite"
    with SqliteSaver.from_conn_string(str(path)) as inner:
        graph = compile_agent(DurableSafeSaver(inner))
        result = run_agent(
            graph,
            question,
            run_id="safe-run",
            trace_store=MemoryTraceStore(),
        )
        assert result["answer"] == answer
    blob = path.read_bytes()
    assert question.encode() not in blob
    assert answer.encode() not in blob


def test_trace_does_not_keep_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.agent.graph.load_settings", lambda **_kwargs: __import__("types").SimpleNamespace(k=5, min_score=0.4))
    monkeypatch.setattr("app.agent.graph.retrieve", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.agent.graph.generate_answer", lambda *_args, **_kwargs: "unused")
    monkeypatch.setattr("app.agent.graph.propose_memory", lambda *_args, **_kwargs: None)
    store = MemoryTraceStore()
    graph = compile_agent(InMemorySaver())
    run_agent(graph, "What time does the desk open?", run_id="trace-safe", trace_store=store)
    events = store.list("trace-safe")
    assert events
    assert all(event["answer"] == "" for event in events)
    assert "What time does the desk open?" not in repr(events)


def test_blocked_attempt_is_absent_from_logs(caplog: pytest.LogCaptureFixture) -> None:
    secret = "patient Alex Example"
    caplog.set_level(logging.INFO)
    result = validate_memory_text(f"Remember that {secret} cancelled.")
    logging.getLogger("healthcore.agent").info("agent_memory_blocked reason=%s", result.reason_codes[0])
    assert secret not in caplog.text
    assert "patient_identifier" in caplog.text
