"""State helpers for the local chat CLI."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_intelligence_systems.contracts.common import (
    ActorContext,
    ActorType,
    BookingContext,
    ConversationContext,
    PolicyContext,
    Proposal,
)
from agentic_intelligence_systems.contracts.private_api import RespondRequest


DEFAULT_ALLOWED_TOOLS = [
    "create_booking",
    "create_service_booking",
    "create_service_request",
    "validate_guest_check_in",
]


@dataclass(slots=True)
class ChatState:
    actor_type: ActorType = ActorType.GUEST
    user_id: str = "user_1"
    internal_staff_id: str | None = None
    conversation_id: str = "terminal_chat"
    channel: str = "terminal"
    language: str = "en"
    resort_id: str | None = None
    booking_id: str | None = None
    room_id: str | None = None
    booking_status: str | None = None
    allowed_tool_names: list[str] = field(
        default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS)
    )
    latest_proposals: list[Proposal] = field(default_factory=list)
    turn_index: int = 0

    def build_request(self, content: str) -> RespondRequest:
        self.turn_index += 1
        suffix = str(self.turn_index)
        return RespondRequest(
            request_id=f"chat_req_{suffix}",
            trace_id=f"chat_trace_{suffix}",
            actor=ActorContext(
                actor_type=self.actor_type,
                user_id=self.user_id,
                internal_staff_id=self.internal_staff_id,
            ),
            conversation=ConversationContext(
                conversation_id=self.conversation_id,
                channel=self.channel,
                language=self.language,
            ),
            booking_context=BookingContext(
                booking_id=self.booking_id,
                room_id=self.room_id,
                resort_id=self.resort_id,
                status=self.booking_status,
            ),
            message={
                "message_id": f"chat_msg_{suffix}",
                "content": content,
            },
            policy_context=PolicyContext(
                proposal_required_for_writes=True,
                allowed_tool_names=self.allowed_tool_names,
            ),
        )

    def summary(self) -> str:
        tools = ", ".join(self.allowed_tool_names) or "none"
        return (
            f"actor={self.actor_type.value}, user={self.user_id}, "
            f"staff={self.internal_staff_id or '-'}, resort={self.resort_id or '-'}, "
            f"booking={self.booking_id or '-'}, room={self.room_id or '-'}, "
            f"status={self.booking_status or '-'}, proposals={len(self.latest_proposals)}, "
            f"tools={tools}"
        )


def parse_tools(value: str) -> list[str]:
    text = value.strip().lower()
    if text == "all":
        return list(DEFAULT_ALLOWED_TOOLS)
    if text == "none":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
