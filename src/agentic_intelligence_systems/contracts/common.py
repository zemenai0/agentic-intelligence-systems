"""Common request and response models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActorType(StrEnum):
    GUEST = "guest"
    STAFF = "staff"
    MANAGER = "manager"
    ADMIN = "admin"


class ResponseType(StrEnum):
    ASSISTANT_MESSAGE = "assistant_message"
    ASSISTANT_MESSAGE_WITH_PROPOSALS = "assistant_message_with_proposals"
    HANDOVER_REQUIRED = "handover_required"
    CLARIFICATION_REQUIRED = "clarification_required"


class RiskLevel(StrEnum):
    LOW_OPERATIONAL = "low_operational"
    MEDIUM_TRANSACTIONAL = "medium_transactional"
    HIGH_POLICY = "high_policy"


class HandoverReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    POLICY_BLOCK = "policy_block"
    TOOL_FAILURE = "tool_failure"
    HUMAN_RECOVERY = "human_recovery"


class ToolType(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


class ContractModel(BaseModel):
    """Base model with strict field validation."""

    model_config = ConfigDict(extra="forbid")


class ActorContext(ContractModel):
    actor_type: ActorType
    user_id: str | None = None
    internal_staff_id: str | None = None


class ConversationContext(ContractModel):
    conversation_id: str
    channel: str
    language: str = "en"


class BookingContext(ContractModel):
    booking_id: str | None = None
    room_id: str | None = None
    resort_id: str | None = None
    status: str | None = None


class MessagePayload(ContractModel):
    message_id: str
    content: str
    role: str = "user"


class PolicyContext(ContractModel):
    proposal_required_for_writes: bool = True
    allowed_tool_names: list[str] = Field(default_factory=list)


class ErrorDetail(ContractModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class AssistantMessage(ContractModel):
    role: str = "assistant"
    content: str


class RoutingDecision(ContractModel):
    primary_agent: str
    confidence: float = Field(ge=0.0, le=1.0)


class Proposal(ContractModel):
    tool_name: str
    action_summary: str
    risk_level: RiskLevel
    arguments: dict[str, Any]
    idempotency_key: str


class HandoverDecision(ContractModel):
    required: bool = True
    reason: HandoverReason
    summary: str
    recommended_queue: str = "front_desk"
