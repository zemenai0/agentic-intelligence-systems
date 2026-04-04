"""Interaction helpers shared across specialized agents."""

from __future__ import annotations

from pydantic import Field

from agentic_intelligence_systems.contracts.common import (
    ContractModel,
    HandoverDecision,
    HandoverReason,
    ResponseType,
    Proposal,
)
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationState,
    DialogueUpdate,
)


class DomainResponse(ContractModel):
    """Normalized agent output before route-level wrapping."""

    response_type: ResponseType
    assistant_text: str | None = None
    proposals: list[Proposal] = Field(default_factory=list)
    handover: HandoverDecision | None = None
    dialogue_update: DialogueUpdate | None = None


class InteractionAgent:
    """Generic interaction behaviors such as clarification and fallback."""

    def handle_message(
        self,
        intent: str,
        message: str | None = None,
        conversation_state: ConversationState | None = None,
    ) -> DomainResponse:
        if intent == "greeting":
            return self.plain_answer(
                self._greeting_text(message, conversation_state),
                dialogue_update=DialogueUpdate(
                    active_intent="general_support",
                    active_agent="InteractionAgent",
                ),
            )
        if intent == "identity":
            return self.plain_answer(
                "I'm HabitaLife's digital concierge. I can help with bookings, arrival "
                "guidance, in-stay requests, recommendations, and broader guest questions.",
                dialogue_update=DialogueUpdate(
                    active_intent="general_support",
                    active_agent="InteractionAgent",
                ),
            )
        if intent == "hostile_repair":
            return self.plain_answer(
                "I've clearly hit a wall, and I want to make this right. Let's drop the "
                "previous thread and start fresh. What's the main thing I can help with "
                "right now?",
                dialogue_update=self._soft_reset_update(),
            )
        return self.plain_answer(
            self._general_support_text(message),
            dialogue_update=DialogueUpdate(
                active_intent="general_support",
                active_agent="InteractionAgent",
            ),
        )

    def plain_answer(
        self,
        text: str,
        dialogue_update: DialogueUpdate | None = None,
    ) -> DomainResponse:
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=text,
            dialogue_update=dialogue_update,
        )

    def clarification(self, text: str) -> DomainResponse:
        return DomainResponse(
            response_type=ResponseType.CLARIFICATION_REQUIRED,
            assistant_text=text,
        )

    def handover(self, summary: str, reason: HandoverReason) -> DomainResponse:
        return DomainResponse(
            response_type=ResponseType.HANDOVER_REQUIRED,
            assistant_text="A staff member should continue this request to avoid delays.",
            handover=HandoverDecision(reason=reason, summary=summary),
        )

    def _greeting_text(
        self,
        message: str | None,
        conversation_state: ConversationState | None,
    ) -> str:
        if message and self._mentions_travel(message):
            return (
                "Hello. That sounds exciting. If you're planning a stay or looking for "
                "ideas for the trip, tell me where and when you're traveling and I'll "
                "help you shape it."
            )
        if conversation_state and conversation_state.goal_summary:
            return (
                "Hello again. "
                f"We were working on {conversation_state.goal_summary}. "
                "If you want, we can keep going or switch to something else."
            )
        return "Hello. What can I help you with today?"

    def _general_support_text(self, message: str | None) -> str:
        if message and self._mentions_travel(message):
            return (
                "That sounds exciting. Tell me the destination, timing, or kind of stay "
                "you have in mind, and I'll help you plan the next step."
            )
        return "Happy to help. Tell me what you want to do, and I'll take it from there."

    def _mentions_travel(self, message: str) -> bool:
        lowered = message.lower()
        return any(
            phrase in lowered
            for phrase in {
                "visit",
                "travel",
                "trip",
                "vacation",
                "holiday",
                "coming to",
                "excited to",
            }
        )

    def _soft_reset_update(self) -> DialogueUpdate:
        return DialogueUpdate(
            active_intent="general_support",
            active_agent="InteractionAgent",
            clear_fields=[
                "active_intent",
                "active_agent",
                "goal_summary",
                "availability_status",
                "retry_count",
                "selected_resort_name",
                "check_in_date",
                "check_out_date",
                "adults",
                "children",
                "scheduled_date",
                "selected_service_id",
                "selected_service_name",
                "request_type",
                "request_description",
                "missing_fields",
            ],
        )
