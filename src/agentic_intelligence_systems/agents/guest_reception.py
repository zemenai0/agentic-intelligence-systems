"""Check-in support and arrival guidance."""

from __future__ import annotations

from agentic_intelligence_systems.agents.interaction import DomainResponse
from agentic_intelligence_systems.clients.backend_api import BackendAPIClient
from agentic_intelligence_systems.contracts.common import (
    ActorType,
    Proposal,
    ResponseType,
    RiskLevel,
)
from agentic_intelligence_systems.contracts.private_api import RespondRequest
from agentic_intelligence_systems.orchestration.policies import tool_allowed
from agentic_intelligence_systems.utils.helpers import build_idempotency_key


class GuestReceptionCheckInAgent:
    """Handle arrival readiness and staff-assisted validation flows."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend_client = backend_client

    async def handle(self, request: RespondRequest) -> DomainResponse:
        booking_id = request.booking_context and request.booking_context.booking_id
        if not booking_id:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text="Please share the booking you want me to check for arrival readiness.",
            )

        readiness = await self._backend_client.get_check_in_readiness(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            booking_id=booking_id,
        )
        assistant_text = f"Check-in status for {booking_id}: {readiness.status}. {readiness.reason}"

        if request.actor.actor_type != ActorType.STAFF or readiness.status != "eligible":
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=assistant_text,
            )

        if not tool_allowed(request.policy_context, "validate_guest_check_in"):
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=assistant_text,
            )

        proposal = Proposal(
            tool_name="validate_guest_check_in",
            action_summary=f"Validate guest check-in for booking {booking_id}",
            risk_level=RiskLevel.LOW_OPERATIONAL,
            arguments={
                "booking_id": booking_id,
                "verification_source": "staff_assisted",
                "verified_by_staff_id": request.actor.internal_staff_id,
            },
            idempotency_key=build_idempotency_key(
                "check_in",
                booking_id,
                request.actor.internal_staff_id or "",
            ),
        )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE_WITH_PROPOSALS,
            assistant_text=f"{assistant_text} I can prepare the validation proposal now.",
            proposals=[proposal],
        )
