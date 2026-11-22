"""Input screening and output release for the compliance assistant.

Screening, untrusted-data filtering, and output inspection are separate checks.
A failed or unknown decision uses a fixed reply and does not repeat staff text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agent.privacy import is_phi_block, validate_memory_text
from process.rag import QUESTION_MAX_CHARS, normalize_text

PATIENT_REFUSAL = (
    "I cannot discuss an identifiable patient, even as a hypothetical. "
    "Please rephrase this as a de-identified policy question."
)
OVERRIDE_REFUSAL = (
    "I cannot change my role or set aside HealthCore compliance rules. "
    "Ask a HealthCore compliance question and I will help."
)
BREACH_REFUSAL = (
    "I cannot share details of an active or unclosed breach. "
    "Ask about the general reporting procedure, or contact Compliance."
)
VENDOR_REFUSAL = (
    "I cannot share vendor-specific agreement terms. "
    "I can explain the standard BAA or DPA requirement, or you can ask Compliance."
)
PERSONAL_REDIRECT = (
    "I cannot help with personal tasks. "
    "I can help with HealthCore compliance policy, procedures, and clinical protocols."
)
CASUAL_REDIRECT = (
    "Hello. I can help with HealthCore compliance. What policy or procedure should we look at?"
)
JURISDICTION_CLARIFY = (
    "Tell me whether this is a United States or United Kingdom clinic, "
    "and I will look up the approved reporting rule."
)
COMPLIANCE_HANDOFF = (
    "The approved HealthCore material does not settle this. Please contact Compliance."
)
NARROW_REQUEST = "Please ask a narrower, de-identified HealthCore compliance question."
SAFE_OUTPUT = (
    "I cannot share that response. "
    "Please ask a de-identified HealthCore compliance question, or contact Compliance."
)

FIXED_REPLIES = frozenset(
    {
        PATIENT_REFUSAL,
        OVERRIDE_REFUSAL,
        BREACH_REFUSAL,
        VENDOR_REFUSAL,
        PERSONAL_REDIRECT,
        CASUAL_REDIRECT,
        JURISDICTION_CLARIFY,
        COMPLIANCE_HANDOFF,
        NARROW_REQUEST,
        SAFE_OUTPUT,
    }
)

SCOPES = frozenset(
    {"personal", "casual", "clarify", "in_domain", "confirmation", "unknown"}
)

_MARKERS = ("PATIENT-MARKER", "BREACH-MARKER", "VENDOR-TERM-MARKER", "INJECT-MARKER")
_NAME = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
_AGE = re.compile(r"\b(age\s*\d{1,3}|\d{1,3}\s*-?\s*year-?\s*old)\b", re.IGNORECASE)
_DIAGNOSIS = re.compile(r"\b(diagnos\w*|PATIENT-MARKER)\b", re.IGNORECASE)
_CLINIC = re.compile(r"\b(clinic|UK-[A-Z]{3}-\d{2}|US-[A-Z]{3}-\d{2})\b", re.IGNORECASE)
_OVERRIDE = re.compile(
    r"\b("
    r"ignore (all |your |the |previous )?(rules|instructions|policy|compliance|passages)|"
    r"drop (the |your )?compliance|"
    r"disregard (the |your )?(rules|policy|instructions)|"
    r"forget (your |the )?(rules|policy|instructions)|"
    r"you are now|act as|pretend to be|"
    r"replace the healthcore policy|"
    r"reveal (your |the )?(system|instructions|prompt|staff token)|"
    r"internal instruction|"
    r"INJECT-MARKER"
    r")\b",
    re.IGNORECASE,
)
_ACTIVE_BREACH = re.compile(
    r"\b("
    r"active breach|under investigation|unclosed breach|"
    r"records were affected|affected records|discovery time|"
    r"when was the breach discovered|which clinic was breached|"
    r"BREACH-MARKER"
    r")\b",
    re.IGNORECASE,
)
_BREACH_FOLLOWUP = re.compile(
    r"\b(discovery time|when was it discovered|what time was it discovered|"
    r"how many records|record count|which clinic)\b",
    re.IGNORECASE,
)
_GENERAL_REPORT = re.compile(
    r"\b(notification procedure|reporting procedure|how do we report|"
    r"general breach notification|notify the|notification timeline)\b",
    re.IGNORECASE,
)
_PERSONAL = re.compile(
    r"\b(salary|write (me )?(an |a )?(email|essay)|cover letter|"
    r"write (some |me )?code|python script|debug this code|my homework)\b",
    re.IGNORECASE,
)
_TRIVIA = re.compile(r"\b(capital of|who won|recipe for|sports score)\b", re.IGNORECASE)
_DEADLINE = re.compile(
    r"\b(deadline|timeline|notification period|60-day|72-hour|72 hours|60 days)\b",
    re.IGNORECASE,
)
_JURISDICTION = re.compile(
    r"\b(united states|united kingdom|\bus\b|\buk\b|u\.s\.|u\.k\.|hipaa|gdpr|ico)\b",
    re.IGNORECASE,
)
_IN_DOMAIN = re.compile(
    r"\b(hipaa|gdpr|baa|dpa|compliance|policy|procedure|protocol|referral|medicaid|"
    r"medicare|insurance|appointment|incident|ticket|checklist|privacy|consent|"
    r"notification|report|clinic|onboarding|no-show|cancel|reminder)\b",
    re.IGNORECASE,
)
_INCIDENT_ID = re.compile(r"\bHC-\d{6}\b", re.IGNORECASE)
_CONFIRM = re.compile(
    r"\b(yes,\s*save it|save it|no,\s*do not save|do not save|don't save|"
    r"instead remember:|do not remember|don't remember)\b",
    re.IGNORECASE,
)
_MEMORY_INTENT = re.compile(
    r"\b(remember|save this|note that|keep in mind)\b",
    re.IGNORECASE,
)
_CASUAL = re.compile(
    r"^(hi|hello|hey|good morning|good afternoon|thanks|thank you|how are you)\b",
    re.IGNORECASE,
)
_CITED_FILE = re.compile(r"\b[\w.-]+\.(?:md|pdf|txt)\b", re.IGNORECASE)
_VENDOR_DOC = re.compile(r"\b(baa|dpa|business associate agreement|data processing agreement)\b", re.IGNORECASE)
_POSSESSIVE = re.compile(r"\b[A-Z][a-z]+'s\b")
_NAMED_PARTY = re.compile(r"\b(with|for)\s+(?!a\b|the\b|an\b)[A-Z][a-z]{2,}\b")


@dataclass(frozen=True)
class Decision:
    action: str
    reason_code: str
    category: str
    guard: str
    answer: str


@dataclass(frozen=True)
class Release:
    allowed: bool
    answer: str
    reason_code: str
    category: str


def fallback_decision() -> Decision:
    return Decision("redirect", "unresolved", "content", "scope", NARROW_REQUEST)


def security_reasons(text: str, *, breach_context: bool = False) -> tuple[str, ...]:
    """Structural and security findings. This does not decide scope."""

    try:
        reasons: list[str] = []
        if _patient_case(text):
            reasons.append("patient_identifier")
        if "VENDOR-TERM-MARKER" in text or _vendor_specific(text):
            reasons.append("vendor_terms")
        if _OVERRIDE.search(text or ""):
            reasons.append("instruction_override")
        if "BREACH-MARKER" in text or _ACTIVE_BREACH.search(text or ""):
            reasons.append("active_breach")
        elif breach_context and _BREACH_FOLLOWUP.search(text or "") and not _GENERAL_REPORT.search(text or ""):
            reasons.append("breach_followup")
        return tuple(reasons)
    except Exception:
        return ("validator_error",)


def scope_label(text: str) -> str:
    """One scope label. An unrecognized result is unknown."""

    try:
        if _PERSONAL.search(text) or _TRIVIA.search(text):
            label = "personal"
        elif _deadline_without_jurisdiction(text):
            label = "clarify"
        elif _CONFIRM.search(text):
            label = "confirmation"
        elif _INCIDENT_ID.search(text) or _MEMORY_INTENT.search(text) or _IN_DOMAIN.search(text):
            label = "in_domain"
        elif _CASUAL.search(text) and len(text) <= 80:
            label = "casual"
        else:
            label = "unknown"
    except Exception:
        label = "unknown"
    if label not in SCOPES:
        return "unknown"
    return label


def screen_question(question: str, *, breach_context: bool = False, confirmation_open: bool = False) -> Decision:
    cleaned = normalize_text(question or "")
    if not cleaned or len(cleaned) > QUESTION_MAX_CHARS:
        return Decision("allow", "", "", "", "")
    reasons = security_reasons(cleaned, breach_context=breach_context)
    if reasons:
        return _security_decision(reasons[0])
    scope = scope_label(cleaned)
    if confirmation_open and scope in {"unknown", "casual"}:
        return Decision("allow", "", "", "", "")
    return _scope_decision(scope)


def passage_is_unsafe(text: str) -> bool:
    return bool(security_reasons(text))


def keep_passages(passages: list[dict]) -> tuple[list[dict], str]:
    """Drop unsafe passages. The reason is empty when every passage stays."""

    kept: list[dict] = []
    reason = ""
    for item in passages:
        if not isinstance(item, dict):
            reason = reason or "malformed_passage"
            continue
        blob = " ".join(str(item.get(key) or "") for key in ("text", "source_document", "section"))
        reasons = security_reasons(blob)
        if reasons:
            reason = reason or reasons[0]
            continue
        kept.append(item)
    return kept, reason


def keep_notes(notes: list[str]) -> tuple[list[str], str]:
    kept: list[str] = []
    reason = ""
    for note in notes:
        reasons = security_reasons(note)
        if reasons:
            reason = reason or reasons[0]
            continue
        kept.append(note)
    return kept, reason


def tool_row_is_unsafe(row: dict) -> bool:
    blob = " ".join(str(value) for value in row.values())
    return passage_is_unsafe(blob)


def release_answer(answer: str, passages: list[dict] | None = None) -> Release:
    """Inspect a finished answer. Templates pass. Unsafe text is replaced whole."""

    text = (answer or "").strip()
    if text in FIXED_REPLIES:
        return Release(True, text, "", "")
    if not text:
        return Release(False, SAFE_OUTPUT, "empty_output", "structural")
    try:
        reasons = security_reasons(text)
    except Exception:
        return Release(False, SAFE_OUTPUT, "validator_error", "structural")
    if reasons:
        category = "structural" if reasons[0] == "validator_error" else "security"
        return Release(False, SAFE_OUTPUT, reasons[0], category)
    allowed_sources = set()
    for item in passages or []:
        if isinstance(item, dict) and item.get("source_document"):
            allowed_sources.add(str(item["source_document"]))
    for cited in _CITED_FILE.findall(text):
        if cited not in allowed_sources:
            return Release(False, SAFE_OUTPUT, "uncited_source", "content")
    return Release(True, answer, "", "")


def _patient_case(text: str) -> bool:
    if "PATIENT-MARKER" in text:
        return True
    checked = validate_memory_text(text)
    if is_phi_block(checked) and set(checked.reason_codes) - {"clinical_content"}:
        return True
    has_name = _NAME.search(text) is not None
    has_age = _AGE.search(text) is not None
    has_diagnosis = _DIAGNOSIS.search(text) is not None
    has_clinic = _CLINIC.search(text) is not None
    if has_name and (has_age or has_diagnosis):
        return True
    if has_age and has_diagnosis and (has_clinic or has_name):
        return True
    return False


def _vendor_specific(text: str) -> bool:
    if not _VENDOR_DOC.search(text or ""):
        return False
    if _POSSESSIVE.search(text or ""):
        return True
    return _NAMED_PARTY.search(text or "") is not None


def _deadline_without_jurisdiction(text: str) -> bool:
    return _DEADLINE.search(text) is not None and _JURISDICTION.search(text) is None


def _security_decision(reason: str) -> Decision:
    if reason == "validator_error":
        return Decision("block", reason, "structural", "intake", NARROW_REQUEST)
    if reason == "vendor_terms":
        return Decision("block", reason, "security", "scope", VENDOR_REFUSAL)
    if reason == "instruction_override":
        return Decision("block", reason, "security", "scope", OVERRIDE_REFUSAL)
    if reason in {"active_breach", "breach_followup"}:
        return Decision("block", reason, "security", "scope", BREACH_REFUSAL)
    return Decision("block", "patient_identifier", "security", "intake", PATIENT_REFUSAL)


def _scope_decision(scope: str) -> Decision:
    if scope == "personal":
        return Decision("redirect", "personal_task", "content", "scope", PERSONAL_REDIRECT)
    if scope == "casual":
        return Decision("redirect", "casual", "content", "scope", CASUAL_REDIRECT)
    if scope == "clarify":
        return Decision("redirect", "jurisdiction", "content", "scope", JURISDICTION_CLARIFY)
    if scope == "unknown":
        return fallback_decision()
    return Decision("allow", "", "", "", "")
