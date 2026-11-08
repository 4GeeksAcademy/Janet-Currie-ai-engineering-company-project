"""Business state for one support-agent run. The run id stays outside this state."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    retrieved_context: list[dict]
    answer: str
    status: str
    route: str
    incident_id: str
    incident_result: dict | None
    tool_outcome: str
    sources_used: list[str]
