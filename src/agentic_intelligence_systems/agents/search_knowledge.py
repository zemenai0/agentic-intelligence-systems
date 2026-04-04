"""General knowledge and safe FAQ answering."""

from __future__ import annotations

from agentic_intelligence_systems.agents.interaction import DomainResponse
from agentic_intelligence_systems.clients.llm_provider import LLMProvider, LLMProviderError
from agentic_intelligence_systems.contracts.common import ResponseType
from agentic_intelligence_systems.contracts.private_api import RespondRequest
from agentic_intelligence_systems.orchestration.conversation_state import ConversationState


class SearchKnowledgeAgent:
    """Answer broad questions without forcing a task workflow."""

    def __init__(self, llm_provider: LLMProvider):
        self._llm_provider = llm_provider

    async def handle(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None = None,
    ) -> DomainResponse:
        del conversation_state
        system_prompt = (
            "You are HabitaLife's search and knowledge agent. "
            "Answer broad factual questions directly, clearly, and without sounding robotic. "
            "If the topic is off-property, answer it briefly on its own merits rather than "
            "forcing the user back into a booking flow. "
            "If a question requires verified live property data, booking state, or hotel "
            "policy you were not given, say that you do not have the verified property "
            "detail yet and offer to help with bookings, arrivals, services, or staff handoff. "
            "Do not invent prices, room availability, or resort policies."
        )
        user_prompt = (
            f"Language: {request.conversation.language}\n"
            f"Guest question: {request.message.content.strip()}"
        )
        try:
            generation = await self._llm_provider.generate_text(system_prompt, user_prompt)
            answer = generation.text.strip()
        except LLMProviderError:
            answer = (
                "I don't want to guess on a question like that. If you want, ask it again "
                "in a slightly different way and I'll try once more. I can also help right "
                "away with bookings, arrival plans, services, or recommendations."
            )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=answer,
        )
