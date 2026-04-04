"""In-memory conversation state for multi-turn agent flows."""

from __future__ import annotations

from pydantic import Field

from agentic_intelligence_systems.contracts.common import BookingContext, ContractModel


class KnownService(ContractModel):
    id: str
    name: str


class DialogueUpdate(ContractModel):
    active_intent: str | None = None
    active_agent: str | None = None
    goal_summary: str | None = None
    availability_status: str | None = None
    retry_count: int | None = None
    booking_id: str | None = None
    room_id: str | None = None
    resort_id: str | None = None
    selected_resort_name: str | None = None
    booking_status: str | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    adults: int | None = None
    children: int | None = None
    scheduled_date: str | None = None
    selected_service_id: str | None = None
    selected_service_name: str | None = None
    request_type: str | None = None
    request_description: str | None = None
    missing_fields: list[str] | None = None
    known_services: list[KnownService] | None = None
    clear_fields: list[str] = Field(default_factory=list)


class ConversationState(ContractModel):
    conversation_id: str
    active_intent: str | None = None
    active_agent: str | None = None
    goal_summary: str | None = None
    availability_status: str | None = None
    retry_count: int = 0
    booking_id: str | None = None
    room_id: str | None = None
    resort_id: str | None = None
    selected_resort_name: str | None = None
    booking_status: str | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    adults: int | None = None
    children: int | None = None
    scheduled_date: str | None = None
    selected_service_id: str | None = None
    selected_service_name: str | None = None
    request_type: str | None = None
    request_description: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    known_services: list[KnownService] = Field(default_factory=list)

    def merge_booking_context(
        self,
        booking_context: BookingContext | None,
    ) -> BookingContext | None:
        if booking_context is None and not any(
            [self.booking_id, self.room_id, self.resort_id, self.booking_status]
        ):
            return None
        return BookingContext(
            booking_id=(booking_context.booking_id if booking_context else None)
            or self.booking_id,
            room_id=(booking_context.room_id if booking_context else None) or self.room_id,
            resort_id=(booking_context.resort_id if booking_context else None)
            or self.resort_id,
            status=(booking_context.status if booking_context else None)
            or self.booking_status,
        )

    def apply_request_context(self, booking_context: BookingContext | None) -> None:
        if booking_context is None:
            return
        self.booking_id = booking_context.booking_id or self.booking_id
        self.room_id = booking_context.room_id or self.room_id
        self.resort_id = booking_context.resort_id or self.resort_id
        self.booking_status = booking_context.status or self.booking_status

    def apply_update(self, update: DialogueUpdate | None) -> None:
        if update is None:
            return
        for field in update.clear_fields:
            if hasattr(self, field):
                if field in {"missing_fields", "known_services"}:
                    setattr(self, field, [])
                elif field == "retry_count":
                    setattr(self, field, 0)
                else:
                    setattr(self, field, None)
        for field in (
            "active_intent",
            "active_agent",
            "goal_summary",
            "availability_status",
            "booking_id",
            "room_id",
            "resort_id",
            "selected_resort_name",
            "booking_status",
            "check_in_date",
            "check_out_date",
            "adults",
            "children",
            "scheduled_date",
            "selected_service_id",
            "selected_service_name",
            "request_type",
            "request_description",
        ):
            value = getattr(update, field)
            if value is not None:
                setattr(self, field, value)
        if update.retry_count is not None:
            self.retry_count = update.retry_count
        if update.missing_fields is not None:
            self.missing_fields = list(update.missing_fields)
        if update.known_services is not None:
            self.known_services = list(update.known_services)

    def match_known_service(self, message: str) -> KnownService | None:
        lowered = message.lower()
        for item in self.known_services:
            if item.id.lower() in lowered or item.name.lower() in lowered:
                return item
        if self.selected_service_name and self.selected_service_name.lower() in lowered:
            return KnownService(
                id=self.selected_service_id or self.selected_service_name,
                name=self.selected_service_name,
            )
        return None


class ConversationStateStore:
    """Simple in-memory state store keyed by conversation ID."""

    def __init__(self):
        self._states: dict[str, ConversationState] = {}

    def get(self, conversation_id: str) -> ConversationState:
        state = self._states.get(conversation_id)
        if state is None:
            state = ConversationState(conversation_id=conversation_id)
            self._states[conversation_id] = state
        return state

    def update_request_context(
        self,
        conversation_id: str,
        booking_context: BookingContext | None,
    ) -> ConversationState:
        state = self.get(conversation_id)
        state.apply_request_context(booking_context)
        return state

    def apply_update(self, conversation_id: str, update: DialogueUpdate | None) -> None:
        self.get(conversation_id).apply_update(update)
