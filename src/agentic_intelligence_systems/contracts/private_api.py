"""Private backend-to-agent API contracts."""

from __future__ import annotations

from pydantic import Field

from agentic_intelligence_systems.contracts.common import (
    ActorContext,
    AssistantMessage,
    ContractModel,
    ConversationContext,
    ErrorDetail,
    HandoverDecision,
    MessagePayload,
    PolicyContext,
    Proposal,
    BookingContext,
    ResponseType,
    RoutingDecision,
)


class IntentClassification(ContractModel):
    primary: str
    secondary: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class BasePrivateRequest(ContractModel):
    request_id: str
    trace_id: str
    actor: ActorContext
    booking_context: BookingContext | None = None


class RespondRequest(BasePrivateRequest):
    conversation: ConversationContext
    message: MessagePayload
    policy_context: PolicyContext | None = None


class RespondResponse(ContractModel):
    request_id: str
    response_type: ResponseType
    intent: IntentClassification
    assistant_message: AssistantMessage | None = None
    proposals: list[Proposal] = Field(default_factory=list)
    handover: HandoverDecision | None = None
    routing: RoutingDecision
    errors: list[ErrorDetail] = Field(default_factory=list)


class RecommendationScope(ContractModel):
    category: str
    time_window: str | None = None
    max_results: int = Field(default=3, ge=1, le=10)


class RecommendRequest(BasePrivateRequest):
    recommendation_scope: RecommendationScope


class RecommendationItem(ContractModel):
    id: str
    category: str
    title: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class RecommendResponse(ContractModel):
    request_id: str
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    proposals: list[Proposal] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)


class SentimentRequest(ContractModel):
    request_id: str
    trace_id: str
    conversation_id: str
    message: MessagePayload


class SentimentScore(ContractModel):
    label: str
    score: float = Field(ge=-1.0, le=1.0)


class RiskAssessment(ContractModel):
    severity: str
    handover_required: bool


class SentimentResponse(ContractModel):
    request_id: str
    sentiment: SentimentScore
    risk: RiskAssessment
    errors: list[ErrorDetail] = Field(default_factory=list)


class MemorySummarizeRequest(ContractModel):
    request_id: str
    trace_id: str
    conversation_id: str
    booking_id: str | None = None
    user_id: str | None = None
    message_ids: list[str] = Field(default_factory=list)
    messages: list[MessagePayload] = Field(default_factory=list)


class MemorySnapshot(ContractModel):
    scope: str
    summary_text: str
    structured_memory_json: dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class CandidateSignal(ContractModel):
    signal_type: str
    key: str
    value_text: str
    confidence: float = Field(ge=0.0, le=1.0)


class MemorySummarizeResponse(ContractModel):
    request_id: str
    snapshot: MemorySnapshot
    candidate_signals: list[CandidateSignal] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
