"""State-aware continuation routing for the planner."""

from __future__ import annotations

from agentic_intelligence_systems.agents.message_semantics import MessageSemantics
from agentic_intelligence_systems.agents.planner_models import AgentPlan
from agentic_intelligence_systems.contracts.common import BookingContext
from agentic_intelligence_systems.orchestration.conversation_state import ConversationState


ACTIVE_TASK_OVERRIDE_INTENTS = {"general_knowledge", "identity", "hostile_repair"}


def continue_active_task(
    signals: MessageSemantics,
    message: str,
    booking_context: BookingContext | None,
    conversation_state: ConversationState | None,
) -> AgentPlan | None:
    # Keep a clear ongoing task alive across follow-up turns.

    if conversation_state is None or not conversation_state.active_intent:
        return None

    active_intent = conversation_state.active_intent
    if active_intent in {"service_catalog", "service_booking"}:
        if conversation_state.match_known_service(message):
            return _service_booking_plan(0.93)

    if active_intent == "service_booking":
        if (
            signals.dates
            or signals.booking_id
            or signals.suggests_task_continuation()
        ):
            return _service_booking_plan(0.88)

    if active_intent == "booking_search":
        if (
            signals.suggests_booking_search()
            or signals.room_selection_hint
            or signals.suggests_task_continuation()
            or signals.asks_availability
        ):
            return _booking_search_plan(0.82)
        if conversation_state.missing_fields or conversation_state.availability_status in {
            "available_options",
            "unavailable",
            "alternative_options",
        }:
            if signals.suggests_task_continuation():
                return _booking_search_plan(0.8)

    if active_intent == "branch_selection":
        return _booking_search_plan(0.8, read_tools=())

    if active_intent == "booking_lookup":
        if (
            signals.suggests_booking_search()
            or signals.suggests_service_request()
            or signals.suggests_service_booking()
            or signals.suggests_service_catalog()
            or signals.suggests_recommendation()
        ):
            return None
        if signals.requests_booking_lookup_explicitly():
            return AgentPlan(
                primary_intent="booking_lookup",
                primary_agent="BookingAgent",
                confidence=0.86,
                read_tools=("get_booking_record",),
            )
        if signals.booking_identifier_only or signals.suggests_booking_lookup():
            return AgentPlan(
                primary_intent="booking_lookup",
                primary_agent="BookingAgent",
                confidence=0.8,
            )

    if active_intent == "service_request":
        if signals.booking_id or (booking_context and booking_context.booking_id):
            return AgentPlan(
                primary_intent="service_request",
                primary_agent="ServiceRequestAgent",
                confidence=0.89,
                secondary_intents=["housekeeping_request"],
                read_tools=("get_current_stay_context", "get_service_catalog"),
            )
        if conversation_state.missing_fields:
            return AgentPlan(
                primary_intent="service_request",
                primary_agent="ServiceRequestAgent",
                confidence=0.84,
                secondary_intents=["housekeeping_request"],
                read_tools=("get_current_stay_context", "get_service_catalog"),
            )

    if active_intent == "check_in_readiness":
        if signals.booking_id or (booking_context and booking_context.booking_id):
            return AgentPlan(
                primary_intent="check_in_readiness",
                primary_agent="GuestReceptionCheckInAgent",
                confidence=0.88,
                read_tools=("get_check_in_readiness",),
            )
        if signals.suggests_check_in():
            return AgentPlan(
                primary_intent="check_in_readiness",
                primary_agent="GuestReceptionCheckInAgent",
                confidence=0.8,
            )

    return None


def should_override_active_task(signals: MessageSemantics) -> bool:
    """Return whether a new turn should interrupt the active task."""

    if signals.open_intent is None:
        return False
    return signals.open_intent.intent in ACTIVE_TASK_OVERRIDE_INTENTS


def _booking_search_plan(
    confidence: float,
    read_tools: tuple[str, ...] = ("search_room_inventory",),
) -> AgentPlan:
    return AgentPlan(
        primary_intent="booking_search",
        primary_agent="BookingAgent",
        confidence=confidence,
        secondary_intents=["booking_create"],
        read_tools=read_tools,
    )


def _service_booking_plan(confidence: float) -> AgentPlan:
    return AgentPlan(
        primary_intent="service_booking",
        primary_agent="RecommendationAgent",
        confidence=confidence,
        read_tools=("get_service_catalog",),
    )
