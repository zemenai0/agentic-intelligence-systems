"""Shared planner models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AgentPlan:
    # Planner output used by the responder.

    primary_intent: str
    primary_agent: str
    confidence: float
    secondary_intents: list[str] = field(default_factory=list)
    read_tools: tuple[str, ...] = ()
    clarification_message: str | None = None
