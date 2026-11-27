"""Classifier boundaries."""

from __future__ import annotations

import pytest

from pipelines.rfp_intake.classifier import classify
from pipelines.rfp_intake.llm import ModelCallError
from rfp_fixtures import MEDFLOW, MERIDIAN, THAMES


def _accept(system: str, user: str) -> dict:
    del system, user
    return {
        "is_rfp": True,
        "reason_code": "institutional_service_request",
        "confidence": 0.96,
        "evidence_refs": ["Subject"],
        "missing_fields": [],
    }


def test_classifier_accepts_formal_meridian_content() -> None:
    result = classify(MERIDIAN, _accept)
    assert result.is_rfp is True
    assert result.reason_code == "institutional_service_request"


def test_classifier_accepts_informal_thames_content() -> None:
    result = classify(THAMES, _accept)
    assert result.is_rfp is True


def test_classifier_rejects_medflow_vendor_pitch() -> None:
    def reject(system: str, user: str) -> dict:
        del system
        assert "MedFlow" in user
        return {
            "is_rfp": False,
            "reason_code": "not_an_rfp",
            "confidence": 0.91,
            "evidence_refs": ["pitch"],
            "missing_fields": [],
        }

    result = classify(MEDFLOW, reject)
    assert result.is_rfp is False
    assert result.reason_code == "not_an_rfp"


def test_classifier_rejects_malformed_model_output() -> None:
    with pytest.raises(ModelCallError) as caught:
        classify(MERIDIAN, lambda _system, _user: {"is_rfp": "yes"})
    assert caught.value.retryable is False
