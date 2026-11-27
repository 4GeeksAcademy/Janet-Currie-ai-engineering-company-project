"""Privacy gate isolation."""

from __future__ import annotations

from pipelines.rfp_intake.privacy import PHI_DIAGNOSIS_MARKER, PHI_PATIENT_MARKER, inspect_text
from pipelines.rfp_intake.service import result_blob, run_intake
from rfp_fixtures import MERIDIAN


def test_occupational_health_text_is_not_phi() -> None:
    decision = inspect_text(MERIDIAN)
    assert decision.contains_phi is False
    assert decision.reason_code is None


def test_phi_fixture_makes_no_model_calls_and_leaks_no_marker() -> None:
    calls: list[str] = []

    def complete(system: str, user: str) -> dict:
        calls.append(system + user)
        return {}

    markdown = f"Case note for {PHI_PATIENT_MARKER}. {PHI_DIAGNOSIS_MARKER}."
    result = run_intake(ticket_id="ticket-phi", raw_pdf_path="", markdown=markdown, complete=complete)
    blob = result_blob(result)
    assert result.outcome == "discarded"
    assert result.reason_code == "phi_detected"
    assert result.contains_phi is True
    assert result.requires_compliance_review is True
    assert result.calls == []
    assert calls == []
    assert PHI_PATIENT_MARKER not in blob
    assert PHI_DIAGNOSIS_MARKER not in blob
    assert result.departments == []
    assert result.handoff is None


def test_patient_name_and_diagnosis_are_blocked_without_echo() -> None:
    decision = inspect_text("Patient Jane Doe was diagnosed with a private condition.")
    assert decision.contains_phi is True
    assert decision.reason_code == "phi_detected"
    assert "Jane" not in (decision.reason_code or "")
