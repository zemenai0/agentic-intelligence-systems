"""Welcome and branch-introduction behavior for first-contact turns."""

from __future__ import annotations

from agentic_intelligence_systems.agents.interaction import DomainResponse
from agentic_intelligence_systems.clients.backend_api import (
    BackendAPIClient,
    BackendToolError,
)
from agentic_intelligence_systems.contracts.common import ResponseType
from agentic_intelligence_systems.contracts.private_api import RespondRequest
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationState,
    DialogueUpdate,
)


class WelcomeAgent:
    # Introduce platforms and available resort branches.

    def __init__(self, backend_client: BackendAPIClient):
        self._backend_client = backend_client

    async def handle(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None = None,
    ) -> DomainResponse:
        try:
            resorts = await self._backend_client.get_resort_catalog(
                request_id=request.request_id,
                trace_id=request.trace_id,
                actor=request.actor,
            )
        except BackendToolError:
            resorts = []

        branch_text = self._build_branch_text(resorts)
        if conversation_state and conversation_state.active_intent == "branch_selection":
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    f"{branch_text} Tell me which branch you prefer, and I’ll continue the reservation."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="branch_selection",
                    active_agent="WelcomeAgent",
                    goal_summary="choosing a resort branch",
                    missing_fields=["resort_id"],
                ),
            )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=(
                "Welcome to HabitaLife. "
                f"{branch_text} "
                "If you want to reserve, tell me which branch you prefer and I’ll guide the booking."
            ),
            dialogue_update=DialogueUpdate(
                active_intent="branch_selection",
                active_agent="WelcomeAgent",
                goal_summary="choosing a resort branch",
                missing_fields=["resort_id"],
            ),
        )

    def _build_branch_text(self, resorts) -> str:
        if not resorts:
            return "I can help with resort stays, booking guidance, and in-stay services."
        if len(resorts) == 1:
            resort = resorts[0]
            location = f" in {resort.location}" if resort.location else ""
            return f"Our current branch is {resort.name}{location}."
        names = []
        for resort in resorts[:4]:
            location = f" in {resort.location}" if resort.location else ""
            names.append(f"{resort.name}{location}")
        return f"Our branches currently include {', '.join(names)}."
