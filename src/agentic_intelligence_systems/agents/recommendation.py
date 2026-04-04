"""Recommendation ranking for guest discovery and upsell flows."""

from __future__ import annotations

from agentic_intelligence_systems.agents.interaction import DomainResponse
from agentic_intelligence_systems.clients.backend_api import BackendAPIClient
from agentic_intelligence_systems.contracts.common import Proposal, ResponseType, RiskLevel
from agentic_intelligence_systems.contracts.private_api import (
    RecommendRequest,
    RecommendResponse,
    RecommendationItem,
    RespondRequest,
)
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationState,
    DialogueUpdate,
    KnownService,
)
from agentic_intelligence_systems.orchestration.policies import tool_allowed
from agentic_intelligence_systems.utils.dates import extract_stay_dates
from agentic_intelligence_systems.utils.helpers import (
    build_idempotency_key,
    extract_booking_id,
    truncate_text,
)


class RecommendationAgent:
    """Rank service catalog items into concise recommendation outputs."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend_client = backend_client

    async def recommend(self, request: RecommendRequest) -> RecommendResponse:
        items = await self._rank_catalog(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            resort_id=request.booking_context and request.booking_context.resort_id,
            category=request.recommendation_scope.category,
            max_results=request.recommendation_scope.max_results,
        )
        return RecommendResponse(request_id=request.request_id, recommendations=items)

    async def handle_message(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None = None,
    ) -> DomainResponse:
        category = self._extract_category(request.message.content)
        items = await self._rank_catalog(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            resort_id=request.booking_context and request.booking_context.resort_id,
            category=category,
            max_results=3,
        )
        known_services = [KnownService(id=item.id, name=item.title) for item in items]
        if not items:
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text="I could not find a strong recommendation right now.",
            )

        selected_item = self._match_selected_service(
            items,
            request.message.content,
            conversation_state,
        )
        if self._is_prebooking_add_on_flow(request, conversation_state, selected_item):
            return self._build_prebooking_add_on_response(
                request=request,
                item=selected_item,
                known_services=known_services,
                conversation_state=conversation_state,
            )
        if selected_item or conversation_state and conversation_state.active_intent == "service_booking":
            return self._build_service_booking_flow(
                request=request,
                items=items,
                known_services=known_services,
                selected_item=selected_item,
                conversation_state=conversation_state,
            )

        options = ", ".join(item.title for item in items[:3])
        service_label = "service" if len(items[:3]) == 1 else "services"
        assistant_text = (
            f"Available {service_label} right now include {options}. "
            "Tell me the service name you want, and I can prepare it."
        )
        if self._is_prebooking_reservation_context(request, conversation_state):
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=assistant_text,
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=conversation_state.goal_summary if conversation_state else None,
                    availability_status=conversation_state.availability_status if conversation_state else None,
                    resort_id=conversation_state.resort_id if conversation_state else None,
                    selected_resort_name=(
                        conversation_state.selected_resort_name if conversation_state else None
                    ),
                    room_id=conversation_state.room_id if conversation_state else None,
                    check_in_date=conversation_state.check_in_date if conversation_state else None,
                    check_out_date=conversation_state.check_out_date if conversation_state else None,
                    adults=conversation_state.adults if conversation_state else None,
                    children=conversation_state.children if conversation_state else None,
                    known_services=known_services,
                    clear_fields=[
                        "selected_service_id",
                        "selected_service_name",
                        "scheduled_date",
                    ],
                    missing_fields=[],
                ),
            )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=assistant_text,
            dialogue_update=DialogueUpdate(
                active_intent="service_catalog",
                active_agent="RecommendationAgent",
                goal_summary="finding the right service for this stay",
                known_services=known_services,
                clear_fields=[
                    "selected_service_id",
                    "selected_service_name",
                    "scheduled_date",
                ],
            ),
        )

    def _is_prebooking_add_on_flow(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None,
        selected_item: RecommendationItem | None,
    ) -> bool:
        if selected_item is None:
            return False
        return self._is_prebooking_reservation_context(request, conversation_state)

    def _is_prebooking_reservation_context(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None,
    ) -> bool:
        if request.booking_context and request.booking_context.booking_id:
            return False
        if conversation_state is None:
            return False
        return (
            conversation_state.room_id is not None
            and conversation_state.check_in_date is not None
            and conversation_state.check_out_date is not None
        )

    def _build_prebooking_add_on_response(
        self,
        *,
        request: RespondRequest,
        item: RecommendationItem | None,
        known_services: list[KnownService],
        conversation_state: ConversationState | None,
    ) -> DomainResponse:
        if item is None or conversation_state is None:
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text="I can help with add-on services once you choose the room.",
            )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=(
                f"Added {item.title} to this booking plan. If you're ready, say book this room, "
                "or you can ask for another service first."
            ),
            dialogue_update=DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                goal_summary=conversation_state.goal_summary,
                availability_status=conversation_state.availability_status,
                resort_id=conversation_state.resort_id,
                selected_resort_name=conversation_state.selected_resort_name,
                room_id=conversation_state.room_id,
                check_in_date=conversation_state.check_in_date,
                check_out_date=conversation_state.check_out_date,
                adults=conversation_state.adults,
                children=conversation_state.children,
                selected_service_id=item.id,
                selected_service_name=item.title,
                known_services=known_services,
                missing_fields=[],
            ),
        )

    async def _rank_catalog(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor,
        resort_id: str | None,
        category: str,
        max_results: int,
    ) -> list[RecommendationItem]:
        catalog = await self._backend_client.get_service_catalog(
            request_id=request_id,
            trace_id=trace_id,
            actor=actor,
            resort_id=resort_id,
        )
        ranked: list[RecommendationItem] = []
        for index, item in enumerate(catalog[: max_results * 2], start=1):
            confidence = 0.9 if category in item.category.lower() else max(0.45, 0.8 - index * 0.08)
            ranked.append(
                RecommendationItem(
                    id=item.id,
                    category=item.category,
                    title=item.name,
                    reason=truncate_text(
                        f"Selected from the live service catalog for guests looking for {category} experiences."
                    ),
                    confidence=confidence,
                )
            )
        ranked.sort(key=lambda entry: entry.confidence, reverse=True)
        return ranked[:max_results]

    def _extract_category(self, message: str) -> str:
        lowered = message.lower()
        for category in ("spa", "dining", "transport", "housekeeping", "maintenance"):
            if category in lowered:
                return category
        return "general"

    def _match_selected_service(
        self,
        items: list[RecommendationItem],
        message: str,
        conversation_state: ConversationState | None,
    ) -> RecommendationItem | None:
        lowered = message.lower()
        for item in items:
            if item.id.lower() in lowered or item.title.lower() in lowered:
                return item
        if conversation_state:
            known_service = conversation_state.match_known_service(message)
            if known_service:
                for item in items:
                    if item.id == known_service.id or item.title == known_service.name:
                        return item
        return None

    def _build_service_booking_flow(
        self,
        *,
        request: RespondRequest,
        items: list[RecommendationItem],
        known_services: list[KnownService],
        selected_item: RecommendationItem | None,
        conversation_state: ConversationState | None,
    ) -> DomainResponse:
        item = selected_item or self._restore_selected_item(items, conversation_state)
        if item is None:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text="Please tell me which service you would like me to prepare.",
                dialogue_update=DialogueUpdate(
                    active_intent="service_booking",
                    active_agent="RecommendationAgent",
                    goal_summary="choosing a service to arrange",
                    known_services=known_services,
                    missing_fields=["selected_service_name"],
                ),
            )

        booking_id = (
            request.booking_context and request.booking_context.booking_id
        ) or extract_booking_id(request.message.content) or (
            conversation_state.booking_id if conversation_state else None
        )
        scheduled_date = self._resolve_scheduled_date(request.message.content, conversation_state)
        missing_fields = self._missing_service_booking_fields(booking_id, scheduled_date)
        if missing_fields:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=self._build_missing_field_prompt(item.title, missing_fields),
                dialogue_update=DialogueUpdate(
                    active_intent="service_booking",
                    active_agent="RecommendationAgent",
                    goal_summary=f"arranging {item.title}",
                    booking_id=booking_id,
                    scheduled_date=scheduled_date,
                    selected_service_id=item.id,
                    selected_service_name=item.title,
                    missing_fields=missing_fields,
                    known_services=known_services,
                ),
            )

        if not tool_allowed(request.policy_context, "create_service_booking"):
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    f"{item.title} is available, but service-booking proposals are not "
                    "enabled for this request."
                ),
            )

        proposal = Proposal(
            tool_name="create_service_booking",
            action_summary=f"Add {item.title} to booking {booking_id}",
            risk_level=RiskLevel.MEDIUM_TRANSACTIONAL,
            arguments={
                "booking_id": booking_id,
                "service_id": item.id,
                "quantity": 1,
                "scheduled_at": f"{scheduled_date}T10:00:00.000Z",
            },
            idempotency_key=build_idempotency_key(
                "service_booking",
                booking_id,
                item.id,
                scheduled_date or "",
            ),
        )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE_WITH_PROPOSALS,
            assistant_text=(
                f"{item.title} looks available. I can prepare it for {scheduled_date} "
                "now."
            ),
            proposals=[proposal],
            dialogue_update=DialogueUpdate(
                clear_fields=[
                    "active_intent",
                    "active_agent",
                    "goal_summary",
                    "selected_service_id",
                    "selected_service_name",
                    "scheduled_date",
                    "missing_fields",
                ],
                known_services=known_services,
            ),
        )

    def _restore_selected_item(
        self,
        items: list[RecommendationItem],
        conversation_state: ConversationState | None,
    ) -> RecommendationItem | None:
        if conversation_state is None:
            return None
        for item in items:
            if (
                conversation_state.selected_service_id
                and item.id == conversation_state.selected_service_id
            ) or (
                conversation_state.selected_service_name
                and item.title == conversation_state.selected_service_name
            ):
                return item
        if conversation_state.selected_service_name:
            return RecommendationItem(
                id=conversation_state.selected_service_id
                or conversation_state.selected_service_name,
                category="general",
                title=conversation_state.selected_service_name,
                reason="Recovered from conversation state.",
                confidence=0.8,
            )
        return None

    def _resolve_scheduled_date(
        self,
        message: str,
        conversation_state: ConversationState | None,
    ) -> str | None:
        dates = extract_stay_dates(message)
        if dates:
            return dates[0]
        if conversation_state:
            return conversation_state.scheduled_date
        return None

    def _missing_service_booking_fields(
        self,
        booking_id: str | None,
        scheduled_date: str | None,
    ) -> list[str]:
        missing_fields: list[str] = []
        if not booking_id:
            missing_fields.append("booking_id")
        if not scheduled_date:
            missing_fields.append("scheduled_date")
        return missing_fields

    def _build_missing_field_prompt(
        self,
        service_name: str,
        missing_fields: list[str],
    ) -> str:
        if missing_fields == ["booking_id"]:
            return f"I can prepare {service_name}. Please share the booking ID."
        if missing_fields == ["scheduled_date"]:
            return (
                f"I can prepare {service_name}. What date would you like it?"
            )
        return (
            f"I can prepare {service_name}. Please share the booking ID and the "
            "preferred date."
        )
