"""RFP intake map. Parallel department workers use LangGraph Send."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import ValidationError

from pipelines.rfp_intake.classifier import classify
from pipelines.rfp_intake.conversion import ConversionError, convert_pdf
from pipelines.rfp_intake.llm import ModelCallError, delimit
from pipelines.rfp_intake.metadata import METADATA_SYSTEM, measure, validate_metadata
from pipelines.rfp_intake.orchestrator import build_work_items
from pipelines.rfp_intake.privacy import inspect_text
from pipelines.rfp_intake.schemas import ValidatedMetadata
from pipelines.rfp_intake.state import IntakeState
from pipelines.rfp_intake.synthesizer import HandoffRejected, build_handoff
from pipelines.rfp_intake.workers import run_worker


def convert_node(state: IntakeState) -> dict:
    if state.get("safe_markdown"):
        return {"page_count": state.get("page_count") or 1}
    try:
        text, pages = convert_pdf(Path(state["raw_pdf_path"]))
    except ConversionError as exc:
        if exc.retryable:
            raise
        return {
            "safe_markdown": "",
            "outcome": "failed",
            "outcome_reason_code": "conversion_failed",
        }
    return {"safe_markdown": text, "page_count": pages}


def privacy_node(state: IntakeState) -> dict:
    if state.get("outcome") == "failed":
        return {}
    decision = inspect_text(state.get("safe_markdown") or "")
    if decision.contains_phi:
        return {
            "contains_phi": True,
            "privacy_reason_code": "phi_detected",
            "requires_compliance_review": True,
            "outcome": "discarded",
            "outcome_reason_code": "phi_detected",
            "safe_markdown": "",
        }
    return {
        "contains_phi": False,
        "privacy_reason_code": None,
        "requires_compliance_review": False,
    }


def after_privacy(state: IntakeState) -> str:
    if state.get("contains_phi") or state.get("outcome") in {"discarded", "failed"}:
        return "end"
    return "extract"


def extract_node(state: IntakeState, complete) -> dict:
    markdown = state.get("safe_markdown") or ""
    _user, truncated = delimit(markdown)
    readability = measure(markdown, page_count=state.get("page_count"))
    try:
        raw = complete(METADATA_SYSTEM, _user)
        metadata = validate_metadata(raw)
    except ModelCallError:
        raise
    except (ValidationError, TypeError, ValueError) as exc:
        raise ModelCallError("processing_failed", retryable=False) from exc
    return {
        "readability": readability.model_dump(),
        "metadata": metadata.model_dump(),
        "truncated": truncated,
    }


def classify_node(state: IntakeState, complete) -> dict:
    try:
        result = classify(state.get("safe_markdown") or "", complete)
    except ModelCallError:
        raise
    if not result.is_rfp:
        return {
            "classification": result.model_dump(),
            "outcome": "discarded",
            "outcome_reason_code": "not_an_rfp",
            "safe_markdown": "",
        }
    return {"classification": result.model_dump(), "outcome": "analyzing"}


def after_classify(state: IntakeState) -> str:
    if state.get("outcome") == "discarded" or state.get("outcome") == "failed":
        return "end"
    classification = state.get("classification") or {}
    if not classification.get("is_rfp"):
        return "end"
    return "orchestrate"


def orchestrate_node(state: IntakeState) -> dict:
    metadata = ValidatedMetadata.model_validate(state.get("metadata") or {})
    items = build_work_items(state.get("safe_markdown") or "", metadata)
    return {"work_items": items, "rfp_id": state.get("rfp_id") or str(uuid4())}


def fan_out(state: IntakeState):
    items = state.get("work_items") or []
    if not items:
        return END
    return [
        Send(
            "department_worker",
            {"work_item": item, "ticket_id": state.get("ticket_id", "")},
        )
        for item in items
    ]


def worker_node(state: IntakeState, complete) -> dict:
    result = run_worker(state["work_item"], complete)
    return {"department_results": [result]}


def synthesize_node(state: IntakeState) -> dict:
    metadata = ValidatedMetadata.model_validate(state.get("metadata") or {})
    excerpts = {
        item["department_id"]: item.get("excerpt") or ""
        for item in state.get("work_items") or []
    }
    try:
        handoff = build_handoff(
            ticket_id=state["ticket_id"],
            rfp_id=state.get("rfp_id") or "",
            metadata=metadata,
            results=list(state.get("department_results") or []),
            excerpts=excerpts,
        )
    except HandoffRejected as exc:
        return {
            "outcome": "failed",
            "outcome_reason_code": "processing_failed",
            "safe_markdown": "",
            "handoff_error": exc.reason_code,
        }
    return {
        "handoff": handoff.model_dump(),
        "outcome": "intake_complete",
        "outcome_reason_code": None,
        "contains_phi": False,
        "safe_markdown": "",
    }


def build_graph(complete):
    graph = StateGraph(IntakeState)
    graph.add_node("convert", convert_node)
    graph.add_node("privacy", privacy_node)
    graph.add_node("extract", lambda state: extract_node(state, complete))
    graph.add_node("classify", lambda state: classify_node(state, complete))
    graph.add_node("orchestrate", orchestrate_node)
    graph.add_node("department_worker", lambda state: worker_node(state, complete))
    graph.add_node("synthesize", synthesize_node)
    graph.add_edge(START, "convert")
    graph.add_edge("convert", "privacy")
    graph.add_conditional_edges("privacy", after_privacy, {"extract": "extract", "end": END})
    graph.add_edge("extract", "classify")
    graph.add_conditional_edges(
        "classify",
        after_classify,
        {"orchestrate": "orchestrate", "end": END},
    )
    graph.add_conditional_edges("orchestrate", fan_out, ["department_worker"])
    graph.add_edge("department_worker", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()
