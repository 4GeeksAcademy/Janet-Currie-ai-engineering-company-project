"""The support-agent map. It searches once and writes only when passages exist."""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar

from langgraph.graph import END, START, StateGraph

from app.agent.incidents import (
    INCIDENT_ID_RE,
    INVALID_INCIDENT_ID,
    incident_answer,
    lookup_incident,
    staff_token_var,
)
from app.agent.memory_policy import (
    asks_to_remember,
    classify_reply,
    propose_memory,
    select_memories,
    should_propose,
    subject_key,
)
from app.agent.privacy import PRIVACY_REFUSAL, is_phi_block, validate_memory_text
from app.agent.state import AgentState
from pipelines.rag import (
    GenerationUnavailableError,
    RetrievalError,
    RetrievalUnavailableError,
    generate_answer,
    retrieve,
)
from process.rag import (
    QUESTION_MAX_CHARS,
    ConfigurationError,
    EmbeddingError,
    load_settings,
    normalize_text,
)

logger = logging.getLogger("healthcore.agent")

SEARCH_UNAVAILABLE = "The knowledge search is unavailable. Please try again."
ANSWER_UNAVAILABLE = "The answer service is unavailable. Please try again."
NOT_CONFIGURED = "The knowledge assistant is not configured. Please try again later."
NO_MATCH_ANSWER = (
    "The HealthCore knowledge base does not contain enough information, "
    "and the coordinator should check with the right team."
)
QUESTION_REQUIRED = "Question is required"
QUESTION_TOO_LONG = "Question is too long."
POLICY_CUES = (
    "referral",
    "escalat",
    "business day",
    "medicaid",
    "cancel",
    "appointment",
    "insurance",
    "reminder",
    "no-show",
    "no show",
    "checklist",
)
TICKET_WORD = re.compile(r"\b(tickets?|incidents?)\b", re.IGNORECASE)
OTHER_NUMBER = re.compile(r"\b\d{2,}\b")

_trace_store: ContextVar[object | None] = ContextVar("agent_trace_store", default=None)
_run_id: ContextVar[str | None] = ContextVar("agent_run_id", default=None)
_memory_store: ContextVar[object | None] = ContextVar("agent_memory_store", default=None)
_owner_id: ContextVar[str | None] = ContextVar("agent_owner_id", default=None)
_conversation_id: ContextVar[str | None] = ContextVar("agent_conversation_id", default=None)
_decision_note: ContextVar[str | None] = ContextVar("agent_decision_note", default=None)


def _failed(message: str) -> dict:
    return {"status": "failed", "answer": message}


def _source_names(passages: list[dict]) -> list[str]:
    names: list[str] = []
    for item in passages:
        name = item.get("source_document") if isinstance(item, dict) else None
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return names


def _write_trace(node: str, state: AgentState) -> None:
    store = _trace_store.get()
    run_id = _run_id.get()
    if store is None or not run_id:
        return
    passages = state.get("retrieved_context") or []
    event = {
        "run_id": run_id,
        "node": node,
        "status": state.get("status") or "",
        "passage_count": len(passages),
        "source_documents": _source_names(passages),
        "answer": "",
        "route": state.get("route") or "",
        "tool_outcome": state.get("tool_outcome") or "",
        "incident_id": state.get("incident_id") or "",
    }
    try:
        store.append(run_id, event)  # type: ignore[attr-defined]
    except Exception:
        logger.info("agent_trace_write_failed node=%s", node)


def _traced(name: str, function):
    def node(state: AgentState) -> dict:
        try:
            update = function(state)
        except Exception:
            message = SEARCH_UNAVAILABLE if name == "retrieve" else ANSWER_UNAVAILABLE
            update = _failed(message)
            logger.info("agent_node_failed node=%s", name)
        _write_trace(name, {**state, **update})
        return update

    return node


def validate_question(state: AgentState) -> dict:
    cleaned = normalize_text(state.get("question") or "")
    if not cleaned:
        return {
            "question": "",
            "retrieved_context": [],
            "answer": QUESTION_REQUIRED,
            "status": "invalid",
        }
    if len(cleaned) > QUESTION_MAX_CHARS:
        return {
            "question": cleaned,
            "retrieved_context": [],
            "answer": QUESTION_TOO_LONG,
            "status": "invalid",
        }
    return {
        "question": cleaned,
        "retrieved_context": [],
        "answer": "",
        "status": "checked",
    }


def search_once(state: AgentState) -> dict:
    try:
        settings = load_settings(require_score=True)
        if settings.min_score is None:
            raise ConfigurationError("RAG_MIN_SCORE is not set.")
        passages = retrieve(
            state.get("question") or "",
            k=settings.k,
            min_score=settings.min_score,
        )
    except ConfigurationError:
        return {**_failed(NOT_CONFIGURED), "sources_used": _sources(state, "rag")}
    except (RetrievalUnavailableError, RetrievalError, EmbeddingError):
        return {**_failed(SEARCH_UNAVAILABLE), "sources_used": _sources(state, "rag")}
    return {
        "retrieved_context": passages,
        "status": "retrieved",
        "answer": "",
        "sources_used": _sources(state, "rag"),
    }


def write_answer(state: AgentState) -> dict:
    passages = state.get("retrieved_context") or []
    notes = _notes(state)
    try:
        if notes:
            answer = generate_answer(state.get("question") or "", passages, memories=notes)
        else:
            answer = generate_answer(state.get("question") or "", passages)
    except ConfigurationError:
        return _failed(NOT_CONFIGURED)
    except (GenerationUnavailableError, EmbeddingError):
        return _failed(ANSWER_UNAVAILABLE)
    return {"answer": answer, "status": "grounded"}


def say_no_match(_state: AgentState) -> dict:
    return {"answer": NO_MATCH_ANSWER, "status": "no_context"}


def _sources(state: AgentState, source: str) -> list[str]:
    sources = list(state.get("sources_used") or [])
    if source not in sources:
        sources.append(source)
    return sources


def choose_source(state: AgentState) -> dict:
    question = state.get("question") or ""
    match = INCIDENT_ID_RE.search(question.upper())
    if match:
        incident_id = match.group(0)
        lowered = question.lower()
        route = "both" if any(cue in lowered for cue in POLICY_CUES) else "incident"
        return {
            "route": route,
            "incident_id": incident_id,
            "tool_outcome": "",
            "status": "routed",
        }
    if TICKET_WORD.search(question) and OTHER_NUMBER.search(question):
        return {
            "route": "invalid_incident",
            "incident_id": "",
            "tool_outcome": "invalid",
            "answer": INVALID_INCIDENT_ID,
            "status": "invalid",
        }
    return {"route": "rag", "incident_id": "", "tool_outcome": "", "status": "routed"}


def lookup_one(state: AgentState) -> dict:
    found = lookup_incident(state.get("incident_id") or "")
    outcome = found["outcome"]
    row = found["incident"]
    update = {
        "tool_outcome": outcome,
        "incident_result": row,
        "sources_used": _sources(state, "incident"),
    }
    if state.get("route") == "both":
        update["status"] = "routed"
        update["answer"] = ""
        return update
    update["answer"] = incident_answer(outcome, row)
    update["status"] = "grounded" if outcome == "found" else "no_context"
    return update


def join_sources(state: AgentState) -> dict:
    passages = state.get("retrieved_context") or []
    if state.get("status") == "failed":
        policy = "The policy part could not be confirmed."
    elif not passages:
        policy = NO_MATCH_ANSWER
    else:
        try:
            if _notes(state):
                policy = generate_answer(state.get("question") or "", passages, memories=_notes(state))
            else:
                policy = generate_answer(state.get("question") or "", passages)
        except (ConfigurationError, GenerationUnavailableError, EmbeddingError):
            policy = "The policy part could not be confirmed."
    incident = incident_answer(state.get("tool_outcome") or "", state.get("incident_result"))
    confirmed = state.get("tool_outcome") == "found" or bool(passages)
    return {
        "answer": f"{policy}\n\n{incident}",
        "status": "grounded" if confirmed else "no_context",
        "sources_used": _sources(state, "rag"),
    }


def _notes(state: AgentState) -> list[str]:
    notes = state.get("memories") or []
    return [note for note in notes if isinstance(note, str) and note.strip()]


def resolve_pending(state: AgentState) -> dict:
    store = _memory_store.get()
    owner = _owner_id.get()
    conversation = _conversation_id.get()
    if store is None or not owner or not conversation:
        return {}
    try:
        pending = store.get_pending(owner, conversation)
    except Exception:
        logger.info("agent_memory_pending_failed")
        return {}
    if pending is None:
        return {}
    decision = classify_reply(state.get("question") or "", pending.content)
    try:
        outcome = store.resolve(
            pending.proposal_id,
            owner_user_id=owner,
            conversation_id=conversation,
            label=decision.label,
            edited_content=decision.edited_content,
        )
    except Exception:
        logger.info("agent_memory_resolve_failed")
        outcome = {"note": "I could not save that. Nothing was stored."}
    note = str(outcome.get("note") or "")
    _decision_note.set(note)
    remainder = (decision.remainder or "").strip()
    if remainder and decision.label in {"approve", "edit", "topic_change"}:
        return {
            "question": remainder,
            "decision": decision.label,
            "decision_note": note,
            "status": "checked",
        }
    return {
        "question": "",
        "answer": note,
        "decision": decision.label,
        "decision_note": note,
        "status": "decision_only",
    }


def recall_memories(state: AgentState) -> dict:
    store = _memory_store.get()
    owner = _owner_id.get()
    if store is None or not owner:
        return {"memories": []}
    try:
        notes = select_memories(store.list_active(owner), state.get("question") or "")
    except Exception:
        logger.info("agent_memory_read_failed")
        notes = []
    return {"memories": notes}


def evaluate_turn(state: AgentState) -> dict:
    answer = state.get("answer") or ""
    if state.get("status") in {"invalid", "failed", "decision_only"}:
        return {"memory_proposal": None}
    store = _memory_store.get()
    owner = _owner_id.get()
    conversation = _conversation_id.get()
    if store is None or not owner or not conversation:
        return {"memory_proposal": None}
    question = state.get("question") or ""
    run_id = _run_id.get() or ""
    try:
        candidate = propose_memory(question, answer)
        if candidate is None and asks_to_remember(question) and is_phi_block(validate_memory_text(question)):
            store.create_proposal(
                owner_user_id=owner,
                conversation_id=conversation,
                run_id=run_id,
                action="add",
                category="operational_correction",
                subject_key="blocked",
                content=question,
                rationale="",
            )
            return {"answer": _with_refusal(answer), "memory_proposal": None}
        if not candidate:
            return {"memory_proposal": None}
        content = str(candidate.get("content") or "")
        if is_phi_block(validate_memory_text(content)):
            store.create_proposal(
                owner_user_id=owner,
                conversation_id=conversation,
                run_id=run_id,
                action=str(candidate.get("action") or "add"),
                category=str(candidate.get("category") or "operational_correction"),
                subject_key=subject_key(str(candidate.get("subject") or "blocked")),
                content=content,
                rationale="",
            )
            return {"answer": _with_refusal(answer), "memory_proposal": None}
        existing = [row.content for row in store.list_active(owner)]
        allowed, reason = should_propose(
            question,
            candidate,
            state.get("retrieved_context") or [],
            existing,
        )
        if not allowed:
            if reason in {
                "patient_identifier",
                "mrn",
                "date_of_birth",
                "clinical_content",
                "insurance_identifier",
                "reidentification",
                "validator_error",
            }:
                return {"answer": _with_refusal(answer), "memory_proposal": None}
            return {"memory_proposal": None}
        action = str(candidate.get("action") or "add")
        key = subject_key(str(candidate.get("subject") or content))
        target = ""
        if action == "forget":
            for row in store.list_active(owner):
                if row.subject_key == key or row.content == content:
                    target = row.memory_id
                    break
        created = store.create_proposal(
            owner_user_id=owner,
            conversation_id=conversation,
            run_id=run_id,
            action=action,
            category=str(candidate["category"]),
            subject_key=key,
            content=content,
            rationale=str(candidate.get("rationale") or "It may help on a later question."),
            target_memory_id=target,
        )
    except Exception:
        logger.info("agent_memory_propose_failed")
        return {"memory_proposal": None}
    pending = created.get("proposal") if created.get("ok") else None
    if pending is None:
        return {"memory_proposal": None}
    shown = f"{answer}\n\nI have not saved this yet. Should I remember it?\n{pending.content}".strip()
    return {
        "answer": shown,
        "memory_proposal": {
            "proposal_id": pending.proposal_id,
            "content": pending.content,
            "status": "pending",
        },
    }


def _with_refusal(answer: str) -> str:
    if PRIVACY_REFUSAL in answer:
        return answer
    return f"{answer}\n\n{PRIVACY_REFUSAL}".strip()


def route_after_resolve(state: AgentState) -> str:
    if state.get("status") == "decision_only":
        return END
    return "validate"


def route_after_validate(state: AgentState) -> str:
    if state.get("status") == "invalid":
        return END
    return "recall"


def route_after_choice(state: AgentState) -> str:
    if state.get("status") == "invalid":
        return END
    if state.get("route") in {"incident", "both"}:
        return "lookup"
    return "retrieve"


def route_after_lookup(state: AgentState) -> str:
    if state.get("route") == "both":
        return "retrieve"
    return "evaluate"


def route_after_retrieve(state: AgentState) -> str:
    if state.get("route") == "both":
        return "join"
    if state.get("status") == "failed":
        return END
    if state.get("retrieved_context"):
        return "generate"
    return "no_match"


def compile_agent(checkpointer):
    """Build the map once. Request code calls the compiled map."""

    builder = StateGraph(AgentState)
    builder.add_node("resolve", _traced("resolve", resolve_pending))
    builder.add_node("validate", _traced("validate", validate_question))
    builder.add_node("recall", _traced("recall", recall_memories))
    builder.add_node("route", _traced("route", choose_source))
    builder.add_node("lookup", _traced("lookup", lookup_one))
    builder.add_node("retrieve", _traced("retrieve", search_once))
    builder.add_node("generate", _traced("generate", write_answer))
    builder.add_node("no_match", _traced("no_match", say_no_match))
    builder.add_node("join", _traced("join", join_sources))
    builder.add_node("evaluate", _traced("evaluate", evaluate_turn))
    builder.add_edge(START, "resolve")
    builder.add_conditional_edges(
        "resolve",
        route_after_resolve,
        {"validate": "validate", END: END},
    )
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {"recall": "recall", END: END},
    )
    builder.add_edge("recall", "route")
    builder.add_conditional_edges(
        "route",
        route_after_choice,
        {"lookup": "lookup", "retrieve": "retrieve", END: END},
    )
    builder.add_conditional_edges(
        "lookup",
        route_after_lookup,
        {"retrieve": "retrieve", "evaluate": "evaluate"},
    )
    builder.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"generate": "generate", "no_match": "no_match", "join": "join", END: END},
    )
    builder.add_edge("generate", "evaluate")
    builder.add_edge("no_match", "evaluate")
    builder.add_edge("join", "evaluate")
    builder.add_edge("evaluate", END)
    return builder.compile(checkpointer=checkpointer)


def run_agent(
    graph,
    question: str,
    *,
    run_id: str,
    trace_store,
    staff_token: str | None = None,
    owner_user_id: str | None = None,
    conversation_id: str | None = None,
    memory_store=None,
) -> dict:
    """Run one question. The staff token stays in a context value, not the checkpoint."""

    store_token = _trace_store.set(trace_store)
    run_token = _run_id.set(run_id)
    auth_token = staff_token_var.set(staff_token)
    memory_token = _memory_store.set(memory_store)
    owner_token = _owner_id.set(owner_user_id)
    conversation_token = _conversation_id.set(conversation_id)
    note_token = _decision_note.set(None)
    try:
        result = graph.invoke(
            {
                "question": question,
                "retrieved_context": [],
                "answer": "",
                "status": "",
                "route": "",
                "incident_id": "",
                "incident_result": None,
                "tool_outcome": "",
                "sources_used": [],
                "owner_user_id": owner_user_id or "",
                "conversation_id": conversation_id or "",
                "memories": [],
                "decision": "",
                "decision_note": "",
                "memory_proposal": None,
            },
            {"configurable": {"thread_id": run_id}},
        )
        note = result.get("decision_note") or _decision_note.get()
        answer = result.get("answer") or ""
        if note and note not in answer:
            result = {**result, "answer": f"{note}\n\n{answer}".strip()}
        return result
    finally:
        _decision_note.reset(note_token)
        _conversation_id.reset(conversation_token)
        _owner_id.reset(owner_token)
        _memory_store.reset(memory_token)
        staff_token_var.reset(auth_token)
        _trace_store.reset(store_token)
        _run_id.reset(run_token)
