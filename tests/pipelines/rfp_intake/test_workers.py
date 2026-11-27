"""Workers, routing, readability, and the handoff."""

from __future__ import annotations

import pytest

from pipelines.rfp_intake.metadata import measure
from pipelines.rfp_intake.orchestrator import build_work_items
from pipelines.rfp_intake.schemas import currency_for, normalize_metadata, select_departments
from pipelines.rfp_intake.service import run_intake
from pipelines.rfp_intake.synthesizer import HandoffRejected, build_handoff
from pipelines.rfp_intake.workers import apply_policy
from pipelines.rfp_intake.privacy import PHI_PATIENT_MARKER
from pipelines.rfp_intake.schemas import DepartmentResult, ValidatedMetadata
from rfp_fixtures import INJECTION, MEDFLOW, MERIDIAN, THAMES, complete_for


def _metadata(**overrides) -> dict:
    raw = {
        "client_name": "Meridian Manufacturing, Inc.",
        "client_country": "US",
        "program_type": "occupational_health",
        "covered_population": 800,
        "deadline": "2026-08-23",
        "budget_range": None,
        "departments_needed": ["sales", "legal", "revenue"],
    }
    raw.update(overrides)
    return raw


def test_unknown_departments_do_not_create_workers() -> None:
    metadata = normalize_metadata(_metadata())
    assert metadata.departments_needed == ["revenue", "clinical", "compliance"]
    assert select_departments(["sales", "legal"]) == ["revenue", "clinical", "compliance"]
    items = build_work_items(MERIDIAN, metadata)
    assert [item["department_id"] for item in items] == ["revenue", "clinical", "compliance"]


def test_country_maps_to_currency_and_agreement() -> None:
    us = normalize_metadata(_metadata())
    uk = normalize_metadata(_metadata(client_country="UK", client_name="Thames Valley University"))
    assert currency_for("US") == "USD"
    assert currency_for("UK") == "GBP"
    assert currency_for(None) is None
    assert us.currency == "USD"
    assert uk.currency == "GBP"
    us_compliance = apply_policy(
        DepartmentResult(department_id="compliance", key_aspects=["HIPAA and data security apply."]),
        us,
    )
    uk_compliance = apply_policy(
        DepartmentResult(department_id="compliance", key_aspects=["UK GDPR and a DPA apply."]),
        uk,
    )
    assert any("BAA" in aspect for aspect in us_compliance["key_aspects"])
    assert any("DPA" in aspect for aspect in uk_compliance["key_aspects"])


def test_missing_budget_population_and_deadline_stay_open_questions() -> None:
    metadata = normalize_metadata(
        _metadata(budget_range=None, covered_population=None, deadline=None, client_country="US")
    )
    assert metadata.budget_range is None
    assert metadata.covered_population is None
    assert metadata.deadline is None
    revenue = apply_policy(DepartmentResult(department_id="revenue", key_aspects=[]), metadata)
    clinical = apply_policy(DepartmentResult(department_id="clinical", key_aspects=[]), metadata)
    assert any("budget" in question.lower() for question in revenue["open_questions"])
    assert any("deadline" in question.lower() for question in revenue["open_questions"])
    assert any("population" in question.lower() for question in clinical["open_questions"])
    assert metadata.covered_population is None


def test_short_text_does_not_crash_readability() -> None:
    empty = measure("")
    short = measure("Hello.")
    long = measure("HealthCore reviews institutional proposals with clear sentences. " * 12)
    assert empty.flesch_reading_ease is None
    assert empty.metric_status == "insufficient_text"
    assert short.word_count == 1
    assert short.flesch_kincaid_grade is None
    assert long.metric_status == "ok"
    assert long.flesch_reading_ease is not None
    assert long.gunning_fog is not None


def test_fan_out_includes_each_department_once() -> None:
    result = run_intake(
        ticket_id="ticket-meridian",
        raw_pdf_path="",
        markdown=MERIDIAN,
        complete=complete_for(MERIDIAN),
    )
    assert result.outcome == "intake_complete"
    assert result.calls.count("revenue") == 1
    assert result.calls.count("clinical") == 1
    assert result.calls.count("compliance") == 1
    assert result.metadata["currency"] == "USD"
    owners = [item["owner"] for item in result.handoff["departments"]]
    assert owners == ["Tom Callahan", "Dr. Marcus Reid", "Claire Whitfield"]


def test_informal_thames_request_is_accepted() -> None:
    result = run_intake(
        ticket_id="ticket-thames",
        raw_pdf_path="",
        markdown=THAMES,
        complete=complete_for(THAMES),
    )
    assert result.outcome == "intake_complete"
    assert result.metadata["client_country"] == "UK"
    assert result.metadata["currency"] == "GBP"
    assert result.handoff["requires_compliance"] is True


def test_vendor_pitch_skips_workers() -> None:
    result = run_intake(
        ticket_id="ticket-medflow",
        raw_pdf_path="",
        markdown=MEDFLOW,
        complete=complete_for(MEDFLOW),
    )
    assert result.outcome == "discarded"
    assert result.reason_code == "not_an_rfp"
    assert "revenue" not in result.calls
    assert result.departments == []


def test_prompt_injection_cannot_add_a_department() -> None:
    result = run_intake(
        ticket_id="ticket-injection",
        raw_pdf_path="",
        markdown=INJECTION,
        complete=complete_for(INJECTION),
    )
    assert result.outcome == "intake_complete"
    ids = [item["department_id"] for item in result.handoff["departments"]]
    assert ids == ["revenue", "clinical", "compliance"]
    assert "sales" not in ids


def test_contradiction_stays_an_open_question() -> None:
    metadata = normalize_metadata(_metadata(covered_population=None))
    results = [
        {
            "department_id": "revenue",
            "key_aspects": ["The covered group is 800 employees."],
            "open_questions": [],
        },
        {
            "department_id": "clinical",
            "key_aspects": ["The covered group is 3000 students."],
            "open_questions": [],
        },
        {
            "department_id": "compliance",
            "key_aspects": ["HIPAA and data security apply."],
            "open_questions": [],
        },
    ]
    excerpts = {
        "revenue": "The covered group is 800 employees.",
        "clinical": "The covered group is 3000 students.",
        "compliance": "HIPAA and data security apply.",
    }
    handoff = build_handoff(
        ticket_id="t",
        rfp_id="r",
        metadata=metadata,
        results=results,
        excerpts=excerpts,
    )
    questions = [question for department in handoff.departments for question in department.open_questions]
    assert any("disagree" in question for question in questions)


def test_synthesizer_rejects_bad_payloads() -> None:
    metadata = normalize_metadata(_metadata())
    base = [
        {"department_id": "revenue", "key_aspects": ["Term is 12 months."], "open_questions": []},
        {"department_id": "clinical", "key_aspects": ["Clinic runs three days."], "open_questions": []},
        {"department_id": "compliance", "key_aspects": ["HIPAA and data security apply."], "open_questions": []},
    ]
    excerpts = {item["department_id"]: item["key_aspects"][0] for item in base}
    with pytest.raises(HandoffRejected):
        build_handoff(ticket_id="t", rfp_id="r", metadata=metadata, results=base[:2], excerpts=excerpts)
    duplicated = base + [dict(base[0])]
    with pytest.raises(HandoffRejected):
        build_handoff(ticket_id="t", rfp_id="r", metadata=metadata, results=duplicated, excerpts=excerpts)
    unknown = [dict(item) for item in base]
    unknown[0] = {**unknown[0], "department_id": "sales"}
    with pytest.raises(HandoffRejected):
        build_handoff(ticket_id="t", rfp_id="r", metadata=metadata, results=unknown, excerpts=excerpts)
    phi = [dict(item) for item in base]
    phi[1] = {**phi[1], "key_aspects": [PHI_PATIENT_MARKER]}
    with pytest.raises(HandoffRejected):
        build_handoff(ticket_id="t", rfp_id="r", metadata=metadata, results=phi, excerpts=excerpts)
    invented = [dict(item) for item in base]
    invented[0] = {**invented[0], "key_aspects": ["HealthCore will charge $50000."]}
    with pytest.raises(HandoffRejected):
        build_handoff(
            ticket_id="t",
            rfp_id="r",
            metadata=metadata,
            results=invented,
            excerpts={"revenue": "Term is 12 months.", "clinical": "Clinic", "compliance": "HIPAA"},
        )


def test_worker_returns_only_its_department() -> None:
    metadata = ValidatedMetadata.model_validate(normalize_metadata(_metadata()).model_dump())
    result = apply_policy(
        DepartmentResult(
            department_id="revenue",
            key_aspects=["The contract term is 12 months."],
            open_questions=["What budget should be priced?"],
            source_references=["Contract"],
        ),
        metadata,
    )
    assert result["department_id"] == "revenue"
    assert result["owner"] == "Tom Callahan"
    assert "proposal section" not in " ".join(result["key_aspects"]).lower()
