"""Intent planning and route selection."""

from __future__ import annotations

from agentic_intelligence_systems.agents.booking_recovery import (
    wants_availability_exploration,
)
from agentic_intelligence_systems.agents.message_semantics import (
    MessageSemantics,
    analyze_message,
)
from agentic_intelligence_systems.agents.planner_models import AgentPlan
from agentic_intelligence_systems.agents.planner_state import (
    continue_active_task,
    should_override_active_task,
)
from agentic_intelligence_systems.contracts.common import BookingContext
from agentic_intelligence_systems.orchestration.conversation_state import ConversationState


PURE_GREETING_MESSAGES = {
    "hi",
    "hey",
    "hello",
    "good morning",
    "good afternoon",
    "good evening",
}


class IntentPlanner:
    """Semantic-first planner with state-aware routing and safe fallbacks."""

    def plan(
        self,
        message: str,
        booking_context: BookingContext | None,
        conversation_state: ConversationState | None = None,
    ) -> AgentPlan:
        signals = analyze_message(message)

        if signals.suggests_check_in():
            return AgentPlan(
                primary_intent="check_in_readiness",
                primary_agent="GuestReceptionCheckInAgent",
                confidence=0.9,
                read_tools=("get_check_in_readiness",),
            )

        if signals.suggests_branch_catalog():
            return AgentPlan(
                primary_intent="branch_catalog",
                primary_agent="WelcomeAgent",
                confidence=0.9,
                read_tools=("get_resort_catalog",),
            )

        if signals.suggests_service_catalog():
            return AgentPlan(
                primary_intent="service_catalog",
                primary_agent="RecommendationAgent",
                confidence=0.88,
                read_tools=("get_service_catalog",),
            )

        if signals.suggests_service_request():
            return AgentPlan(
                primary_intent="service_request",
                primary_agent="ServiceRequestAgent",
                confidence=0.9,
                secondary_intents=["housekeeping_request"],
                read_tools=("get_current_stay_context", "get_service_catalog"),
            )

        if signals.suggests_service_booking(
            has_known_service=self._has_known_service(message, conversation_state)
        ):
            return AgentPlan(
                primary_intent="service_booking",
                primary_agent="RecommendationAgent",
                confidence=0.88,
                read_tools=("get_service_catalog",),
            )

        if (
            signals.requests_booking_lookup_explicitly()
            and not signals.suggests_booking_search()
        ):
            return AgentPlan(
                primary_intent="booking_lookup",
                primary_agent="BookingAgent",
                confidence=0.84,
                read_tools=("get_booking_record",),
            )

        state_plan = continue_active_task(
            signals,
            message,
            booking_context,
            conversation_state,
        )
        if state_plan and not should_override_active_task(signals):
            return state_plan

        if self._is_pure_welcome(signals, conversation_state):
            return AgentPlan(
                primary_intent="welcome",
                primary_agent="WelcomeAgent",
                confidence=0.92,
                read_tools=("get_resort_catalog",),
            )

        if self._should_explore_booking_dates(signals, conversation_state):
            return self._booking_search_plan(0.84)

        if signals.suggests_booking_search():
            return self._booking_search_plan(0.84)

        if signals.suggests_recommendation():
            return AgentPlan(
                primary_intent="recommendation",
                primary_agent="RecommendationAgent",
                confidence=0.82,
                read_tools=("get_service_catalog",),
            )

        if signals.suggests_faq():
            return AgentPlan(
                primary_intent="faq_lookup",
                primary_agent="SearchKnowledgeAgent",
                confidence=0.7,
            )

        if signals.open_intent:
            return AgentPlan(
                primary_intent=signals.open_intent.intent,
                primary_agent=signals.open_intent.agent_name,
                confidence=signals.open_intent.confidence,
            )

        return AgentPlan(
            primary_intent="general_support",
            primary_agent="InteractionAgent",
            confidence=0.52,
        )

    def _has_known_service(
        self,
        message: str,
        conversation_state: ConversationState | None,
    ) -> bool:
        if conversation_state is None:
            return False
        return conversation_state.match_known_service(message) is not None

    def _is_pure_welcome(
        self,
        signals: MessageSemantics,
        conversation_state: ConversationState | None,
    ) -> bool:
        if conversation_state and conversation_state.active_intent:
            return False
        if signals.open_intent is None or signals.open_intent.intent != "greeting":
            return False
        return signals.normalized in PURE_GREETING_MESSAGES

    def _should_explore_booking_dates(
        self,
        signals: MessageSemantics,
        conversation_state: ConversationState | None,
    ) -> bool:
        if conversation_state is None:
            return False
        if conversation_state.active_intent != "booking_search":
            return False
        if conversation_state.availability_status not in {
            "unavailable",
            "alternative_options",
        }:
            return False
        return wants_availability_exploration(signals.normalized)

    def _booking_search_plan(self, confidence: float) -> AgentPlan:
        return AgentPlan(
            primary_intent="booking_search",
            primary_agent="BookingAgent",
            confidence=confidence,
            secondary_intents=["booking_create"],
            read_tools=("search_room_inventory",),
        )
