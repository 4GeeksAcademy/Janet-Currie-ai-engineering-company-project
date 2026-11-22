"""Fail-closed checks for text that might be stored as agent memory."""

from __future__ import annotations

import re
from dataclasses import dataclass


PRIVACY_REFUSAL = "HealthCore cannot remember patient or clinical details."

PHI_REASONS = frozenset(
    {
        "patient_identifier",
        "mrn",
        "date_of_birth",
        "clinical_content",
        "insurance_identifier",
        "reidentification",
        "validator_error",
    }
)

_PATIENT_NAME = re.compile(r"\bpatient\s+[A-Z][a-z]+")
_MRN = re.compile(r"\b(mrn|medical record(?: number)?)\b", re.IGNORECASE)
_MRN_TOKEN = re.compile(r"\bMRN[-:\s]*[A-Z0-9]{3,}\b")
_DOB = re.compile(r"\b(date of birth|born on|dob)\b", re.IGNORECASE)
_CLINICAL = re.compile(
    r"\b(diagnosis|diagnosed|symptom|prescription|lab result|clinical note|treatment plan)\b",
    re.IGNORECASE,
)
_INSURANCE = re.compile(
    r"\b(insurance number|member id|subscriber id)\b",
    re.IGNORECASE,
)
_PERSON = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_CLINIC = re.compile(r"\b(?:clinic|[A-Z]{2}-[A-Z]{3}-\d{2})\b", re.IGNORECASE)
_VISIT = re.compile(r"\b(appointment|visit|seen)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PrivacyResult:
    allowed: bool
    reason_codes: tuple[str, ...]
    handling: str


def validate_memory_text(text: str) -> PrivacyResult:
    """Return whether this text may be stored or shown as a memory.

    This function does not log the submitted text. Any unexpected error refuses the text.
    """

    try:
        if not isinstance(text, str) or not text.strip():
            return PrivacyResult(False, ("empty",), "drop")
        reasons: list[str] = []
        if _PATIENT_NAME.search(text):
            reasons.append("patient_identifier")
        if _MRN.search(text) or _MRN_TOKEN.search(text):
            reasons.append("mrn")
        if _DOB.search(text):
            reasons.append("date_of_birth")
        if _CLINICAL.search(text):
            reasons.append("clinical_content")
        if _INSURANCE.search(text):
            reasons.append("insurance_identifier")
        if (
            _PERSON.search(text)
            and _ISO_DATE.search(text)
            and (_CLINIC.search(text) or _VISIT.search(text))
        ):
            reasons.append("reidentification")
        if reasons:
            return PrivacyResult(False, tuple(reasons), "refuse")
        return PrivacyResult(True, (), "keep")
    except Exception:
        return PrivacyResult(False, ("validator_error",), "refuse")


def is_phi_block(result: PrivacyResult) -> bool:
    return not result.allowed and bool(PHI_REASONS.intersection(result.reason_codes))
