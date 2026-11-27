"""One entry point for the worker. It returns a safe result and does not write Markdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from pipelines.rfp_intake.classifier import CLASSIFIER_SYSTEM
from pipelines.rfp_intake.graph import build_graph
from pipelines.rfp_intake.llm import CompleteFn, ModelCallError, live_complete
from pipelines.rfp_intake.metadata import METADATA_SYSTEM
from pipelines.rfp_intake.workers import WORKER_SYSTEM


@dataclass
class IntakeResult:
    outcome: str
    reason_code: str | None
    contains_phi: bool
    requires_compliance_review: bool
    metadata: dict | None = None
    readability: dict | None = None
    departments: list[dict] = field(default_factory=list)
    handoff: dict | None = None
    classification: dict | None = None
    rfp_id: str | None = None
    calls: list[str] = field(default_factory=list)


def run_intake(
    *,
    ticket_id: str,
    raw_pdf_path: str,
    complete: CompleteFn | None = None,
    markdown: str | None = None,
    rfp_id: str | None = None,
) -> IntakeResult:
    calls: list[str] = []
    base = complete or live_complete

    def tracked(system: str, user: str) -> dict:
        if system == CLASSIFIER_SYSTEM:
            calls.append("classifier")
        elif system == METADATA_SYSTEM:
            calls.append("metadata")
        else:
            for department_id, prompt in WORKER_SYSTEM.items():
                if system == prompt:
                    calls.append(department_id)
                    break
            else:
                calls.append("model")
        return base(system, user)

    graph = build_graph(tracked)
    initial = {
        "ticket_id": ticket_id,
        "raw_pdf_path": raw_pdf_path,
        "safe_markdown": markdown or "",
        "department_results": [],
        "contains_phi": False,
        "requires_compliance_review": False,
        "rfp_id": rfp_id or "",
    }
    try:
        final = graph.invoke(initial)
    except ModelCallError as exc:
        if exc.retryable:
            raise
        return IntakeResult(
            outcome="failed",
            reason_code="processing_failed",
            contains_phi=False,
            requires_compliance_review=False,
            calls=calls,
        )
    outcome = final.get("outcome") or "failed"
    if outcome not in {"discarded", "intake_complete", "failed"}:
        outcome = "failed"
    departments = list(final.get("department_results") or [])
    if outcome != "intake_complete":
        departments = []
    return IntakeResult(
        outcome=outcome,
        reason_code=final.get("outcome_reason_code"),
        contains_phi=bool(final.get("contains_phi")),
        requires_compliance_review=bool(final.get("requires_compliance_review")),
        metadata=final.get("metadata") if outcome == "intake_complete" else None,
        readability=final.get("readability") if outcome == "intake_complete" else None,
        departments=departments,
        handoff=final.get("handoff") if outcome == "intake_complete" else None,
        classification=final.get("classification"),
        rfp_id=final.get("rfp_id") if outcome == "intake_complete" else None,
        calls=calls,
    )


def result_blob(result: IntakeResult) -> str:
    """Safe serialized view used by leakage tests. Markdown is not on the result."""

    return str(
        {
            "outcome": result.outcome,
            "reason_code": result.reason_code,
            "contains_phi": result.contains_phi,
            "metadata": result.metadata,
            "departments": result.departments,
            "handoff": result.handoff,
            "classification": result.classification,
        }
    )
