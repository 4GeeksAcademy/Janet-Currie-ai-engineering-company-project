"""Deterministic privacy gate for RFP text. It does not use the staff memory validator."""

from __future__ import annotations

import re
from dataclasses import dataclass

PHI_PATIENT_MARKER = "HC-PHI-PATIENT-MARKER"
PHI_DIAGNOSIS_MARKER = "HC-PHI-DIAGNOSIS-MARKER"

_PATIENT_NAME = re.compile(r"\bpatient\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b")
_MRN = re.compile(r"\b(mrn|medical record(?: number)?)\b[:\s-]*[A-Z0-9]", re.IGNORECASE)
_DOB = re.compile(r"\b(date of birth|born on|dob)\b", re.IGNORECASE)
_DIAGNOSIS = re.compile(r"\bdiagnos(?:is|ed)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PrivacyDecision:
    contains_phi: bool
    reason_code: str | None
    requires_compliance_review: bool


def inspect_text(text: str) -> PrivacyDecision:
    """Return a safe decision. The matched text is not included."""

    try:
        blocked = _blocked(text)
    except Exception:
        blocked = True
    if blocked:
        return PrivacyDecision(True, "phi_detected", True)
    return PrivacyDecision(False, None, False)


def _blocked(text: str) -> bool:
    if not isinstance(text, str) or not text:
        return False
    if PHI_PATIENT_MARKER in text or PHI_DIAGNOSIS_MARKER in text:
        return True
    if _PATIENT_NAME.search(text):
        return True
    if _MRN.search(text):
        return True
    if _DOB.search(text):
        return True
    if _DIAGNOSIS.search(text):
        return True
    return False
