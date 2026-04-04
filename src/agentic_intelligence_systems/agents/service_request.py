"""Service request proposal logic."""

from __future__ import annotations

from agentic_intelligence_systems.agents.interaction import DomainResponse
from agentic_intelligence_systems.clients.backend_api import BackendAPIClient
from agentic_intelligence_systems.contracts.common import (
    HandoverDecision,
    HandoverReason,
    Proposal,
    ResponseType,
    RiskLevel,
)
from agentic_intelligence_systems.contracts.private_api import RespondRequest
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationState,
    DialogueUpdate,
)
from agentic_intelligence_systems.orchestration.policies import tool_allowed
from agentic_intelligence_systems.utils.helpers import (
    build_idempotency_key,
    contains_any,
    extract_booking_id,
)


MAINTENANCE_KEYWORDS = {"ac", "air conditioning", "broken", "repair", "leak", "hot", "cold"}
DINING_KEYWORDS = {"food", "dinner", "breakfast", "lunch", "drink"}
TRANSPORT_KEYWORDS = {"taxi", "airport", "pickup", "dropoff", "shuttle"}


class ServiceRequestAgent:
    """Build safe service request responses and proposals."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend_client = backend_client

    async def handle(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None = None,
    ) -> DomainResponse:
        booking_id = (
            request.booking_context and request.booking_context.booking_id
        ) or extract_booking_id(request.message.content) or (
            conversation_state.booking_id if conversation_state else None
        )
        request_description = self._resolve_request_description(request, conversation_state)
        request_type = self._resolve_request_type(request, conversation_state, request_description)
        if not booking_id:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text="Please share the booking ID for the stay that needs help.",
                dialogue_update=DialogueUpdate(
                    active_intent="service_request",
                    active_agent="ServiceRequestAgent",
                    goal_summary=f"a {request_type} request: {request_description}",
                    request_type=request_type,
                    request_description=request_description,
                    missing_fields=["booking_id"],
                ),
            )

        stay_context = await self._backend_client.get_current_stay_context(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            booking_id=booking_id,
        )
        catalog = await self._backend_client.get_service_catalog(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            resort_id=request.booking_context and request.booking_context.resort_id,
        )

        available_names = [
            item.name
            for item in catalog
            if request_type in item.category.lower() or request_type in item.name.lower()
        ]
        room_label = stay_context.room.room_number if stay_context.room else "your room"
        assistant_text = f"I can route that request for room {room_label}."
        if available_names:
            assistant_text += f" The closest available service is {available_names[0]}."

        if not tool_allowed(request.policy_context, "create_service_request"):
            return DomainResponse(
                response_type=ResponseType.HANDOVER_REQUIRED,
                assistant_text=assistant_text,
                handover=HandoverDecision(
                    reason=HandoverReason.POLICY_BLOCK,
                    summary="Service request write tools were not allowed in policy context.",
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="service_request",
                    active_agent="ServiceRequestAgent",
                    goal_summary=f"a {request_type} request: {request_description}",
                    booking_id=booking_id,
                    request_type=request_type,
                    request_description=request_description,
                    missing_fields=[],
                ),
            )

        proposal = Proposal(
            tool_name="create_service_request",
            action_summary=f"Create {request_type} request for booking {booking_id}",
            risk_level=RiskLevel.LOW_OPERATIONAL,
            arguments={
                "booking_id": booking_id,
                "type": request_type,
                "description": request_description,
            },
            idempotency_key=build_idempotency_key(
                "service_request",
                booking_id,
                request_type,
                request_description,
            ),
        )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE_WITH_PROPOSALS,
            assistant_text=assistant_text,
            proposals=[proposal],
                dialogue_update=DialogueUpdate(
                    booking_id=booking_id,
                    clear_fields=[
                        "active_intent",
                        "active_agent",
                        "goal_summary",
                        "request_type",
                        "request_description",
                        "missing_fields",
                    ],
                ),
        )

    def _infer_request_type(self, message: str) -> str:
        lowered = message.lower()
        if contains_any(lowered, MAINTENANCE_KEYWORDS):
            return "maintenance"
        if contains_any(lowered, DINING_KEYWORDS):
            return "dining"
        if contains_any(lowered, TRANSPORT_KEYWORDS):
            return "transport"
        return "housekeeping"

    def _resolve_request_description(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None,
    ) -> str:
        content = request.message.content.strip()
        if extract_booking_id(content) and conversation_state and conversation_state.request_description:
            return conversation_state.request_description
        return content

    def _resolve_request_type(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None,
        description: str,
    ) -> str:
        if conversation_state and conversation_state.request_type and extract_booking_id(
            request.message.content
        ):
            return conversation_state.request_type
        return self._infer_request_type(description)
