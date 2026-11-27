"""Graph routing for the three intake outcomes."""

from __future__ import annotations

from pipelines.rfp_intake.service import run_intake
from rfp_fixtures import MEDFLOW, MERIDIAN, complete_for


def test_graph_completes_only_after_three_workstreams() -> None:
    result = run_intake(
        ticket_id="graph-1",
        raw_pdf_path="",
        markdown=MERIDIAN,
        complete=complete_for(MERIDIAN),
    )
    assert result.outcome == "intake_complete"
    assert result.handoff["contains_phi"] is False
    assert len(result.handoff["departments"]) == 3


def test_graph_stops_vendor_pitch_before_workers() -> None:
    result = run_intake(
        ticket_id="graph-2",
        raw_pdf_path="",
        markdown=MEDFLOW,
        complete=complete_for(MEDFLOW),
    )
    assert result.outcome == "discarded"
    assert result.reason_code == "not_an_rfp"
    assert result.handoff is None
