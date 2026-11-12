"""The support-agent map. It searches once and writes only when passages exist."""

from __future__ import annotations

import logging
from contextvars import ContextVar

from langgraph.graph import END, START, StateGraph

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

_trace_store: ContextVar[object | None] = ContextVar("agent_trace_store", default=None)
_run_id: ContextVar[str | None] = ContextVar("agent_run_id", default=None)


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
        "answer": state.get("answer") or "",
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
        return _failed(NOT_CONFIGURED)
    except (RetrievalUnavailableError, RetrievalError, EmbeddingError):
        return _failed(SEARCH_UNAVAILABLE)
    return {"retrieved_context": passages, "status": "retrieved", "answer": ""}


def write_answer(state: AgentState) -> dict:
    passages = state.get("retrieved_context") or []
    try:
        answer = generate_answer(state.get("question") or "", passages)
    except ConfigurationError:
        return _failed(NOT_CONFIGURED)
    except (GenerationUnavailableError, EmbeddingError):
        return _failed(ANSWER_UNAVAILABLE)
    return {"answer": answer, "status": "grounded"}


def say_no_match(_state: AgentState) -> dict:
    return {"answer": NO_MATCH_ANSWER, "status": "no_context"}


def route_after_validate(state: AgentState) -> str:
    if state.get("status") == "invalid":
        return END
    return "retrieve"


def route_after_retrieve(state: AgentState) -> str:
    if state.get("status") == "failed":
        return END
    if state.get("retrieved_context"):
        return "generate"
    return "no_match"


def compile_agent(checkpointer):
    """Build the map once. Request code calls the compiled map."""

    builder = StateGraph(AgentState)
    builder.add_node("validate", _traced("validate", validate_question))
    builder.add_node("retrieve", _traced("retrieve", search_once))
    builder.add_node("generate", _traced("generate", write_answer))
    builder.add_node("no_match", _traced("no_match", say_no_match))
    builder.add_edge(START, "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {"retrieve": "retrieve", END: END},
    )
    builder.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"generate": "generate", "no_match": "no_match", END: END},
    )
    builder.add_edge("generate", END)
    builder.add_edge("no_match", END)
    return builder.compile(checkpointer=checkpointer)


def run_agent(graph, question: str, *, run_id: str, trace_store) -> dict:
    """Run one question. The run id is the checkpoint thread id and the trace id."""

    store_token = _trace_store.set(trace_store)
    run_token = _run_id.set(run_id)
    try:
        return graph.invoke(
            {
                "question": question,
                "retrieved_context": [],
                "answer": "",
                "status": "",
            },
            {"configurable": {"thread_id": run_id}},
        )
    finally:
        _trace_store.reset(store_token)
        _run_id.reset(run_token)
