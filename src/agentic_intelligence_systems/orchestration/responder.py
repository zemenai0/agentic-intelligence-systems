"""Main respond-flow orchestration."""

from __future__ import annotations

from agentic_intelligence_systems.agents.booking import BookingAgent
from agentic_intelligence_systems.agents.guest_reception import GuestReceptionCheckInAgent
from agentic_intelligence_systems.agents.interaction import DomainResponse, InteractionAgent
from agentic_intelligence_systems.agents.planner import IntentPlanner
from agentic_intelligence_systems.agents.recommendation import RecommendationAgent
from agentic_intelligence_systems.agents.search_knowledge import SearchKnowledgeAgent
from agentic_intelligence_systems.agents.service_request import ServiceRequestAgent
from agentic_intelligence_systems.agents.welcome import WelcomeAgent
from agentic_intelligence_systems.clients.backend_api import BackendToolError
from agentic_intelligence_systems.clients.llm_provider import LLMProvider, LLMProviderError
from agentic_intelligence_systems.contracts.common import AssistantMessage, ErrorDetail, HandoverReason
from agentic_intelligence_systems.contracts.private_api import (
    IntentClassification,
    RespondRequest,
    RespondResponse,
)
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationState,
    ConversationStateStore,
    DialogueUpdate,
)
from agentic_intelligence_systems.orchestration.policies import validate_policy_context


class AgentResponder:
    """Route conversational requests to the right specialized agent."""

    def __init__(
        self,
        planner: IntentPlanner,
        welcome_agent: WelcomeAgent,
        interaction_agent: InteractionAgent,
        service_request_agent: ServiceRequestAgent,
        booking_agent: BookingAgent,
        guest_reception_agent: GuestReceptionCheckInAgent,
        recommendation_agent: RecommendationAgent,
        search_knowledge_agent: SearchKnowledgeAgent,
        llm_provider: LLMProvider,
        conversation_store: ConversationStateStore,
    ):
        self._planner = planner
        self._welcome_agent = welcome_agent
        self._interaction_agent = interaction_agent
        self._service_request_agent = service_request_agent
        self._booking_agent = booking_agent
        self._guest_reception_agent = guest_reception_agent
        self._recommendation_agent = recommendation_agent
        self._search_knowledge_agent = search_knowledge_agent
        self._llm_provider = llm_provider
        self._conversation_store = conversation_store

    async def respond(self, request: RespondRequest) -> RespondResponse:
        conversation_id = request.conversation.conversation_id
        conversation_state = self._conversation_store.update_request_context(
            conversation_id,
            request.booking_context,
        )
        request = request.model_copy(
            update={
                "booking_context": conversation_state.merge_booking_context(
                    request.booking_context
                )
            }
        )
        policy_error = validate_policy_context(request.policy_context)
        if policy_error:
            return self._build_response(
                request=request,
                plan_primary="InteractionAgent",
                intent_primary="general_support",
                confidence=0.0,
                domain_response=self._interaction_agent.handover(
                    "Policy context was missing from the backend request.",
                    HandoverReason.POLICY_BLOCK,
                ),
                errors=[policy_error],
            )

        plan = self._planner.plan(
            request.message.content,
            request.booking_context,
            conversation_state,
        )
        if plan.clarification_message and self._should_dispatch_clarification(plan.primary_agent):
            return await self._respond_with_agent(
                request,
                plan,
                conversation_id,
                conversation_state,
            )

        if plan.clarification_message:
            self._conversation_store.apply_update(
                conversation_id,
                self._clarification_update(plan.primary_intent, plan.primary_agent),
            )
            return self._build_response(
                request=request,
                plan_primary=plan.primary_agent,
                intent_primary=plan.primary_intent,
                confidence=plan.confidence,
                domain_response=self._interaction_agent.clarification(
                    plan.clarification_message
                ),
                secondary_intents=plan.secondary_intents,
            )

        return await self._respond_with_agent(
            request,
            plan,
            conversation_id,
            conversation_state,
        )

    async def _respond_with_agent(
        self,
        request: RespondRequest,
        plan,
        conversation_id: str,
        conversation_state: ConversationState,
    ) -> RespondResponse:
        try:
            domain_response = await self._dispatch(
                plan.primary_agent,
                plan.primary_intent,
                request,
                conversation_state,
            )
        except BackendToolError as exc:
            domain_response = self._interaction_agent.handover(
                "Required backend context could not be loaded.",
                HandoverReason.TOOL_FAILURE,
            )
            errors = [ErrorDetail(code="tool_unavailable", message=str(exc))]
            return self._build_response(
                request=request,
                plan_primary=plan.primary_agent,
                intent_primary=plan.primary_intent,
                confidence=plan.confidence,
                domain_response=domain_response,
                secondary_intents=plan.secondary_intents,
                errors=errors,
            )

        self._conversation_store.apply_update(
            conversation_id,
            domain_response.dialogue_update,
        )
        return self._build_response(
            request=request,
            plan_primary=plan.primary_agent,
            intent_primary=plan.primary_intent,
            confidence=plan.confidence,
            domain_response=await self._polish_response(plan.primary_agent, domain_response),
            secondary_intents=plan.secondary_intents,
        )

    def _should_dispatch_clarification(self, agent_name: str) -> bool:
        return agent_name == "ServiceRequestAgent"

    async def _dispatch(
        self,
        agent_name: str,
        intent_name: str,
        request: RespondRequest,
        conversation_state: ConversationState,
    ) -> DomainResponse:
        if agent_name == "ServiceRequestAgent":
            return await self._service_request_agent.handle(request, conversation_state)
        if agent_name == "BookingAgent":
            return await self._booking_agent.handle(request, conversation_state)
        if agent_name == "GuestReceptionCheckInAgent":
            return await self._guest_reception_agent.handle(request)
        if agent_name == "RecommendationAgent":
            return await self._recommendation_agent.handle_message(
                request,
                conversation_state,
            )
        if agent_name == "SearchKnowledgeAgent":
            return await self._search_knowledge_agent.handle(request, conversation_state)
        if agent_name == "WelcomeAgent":
            return await self._welcome_agent.handle(request, conversation_state)
        return self._interaction_agent.handle_message(
            intent_name,
            request.message.content,
            conversation_state,
        )

    async def _polish_response(
        self,
        agent_name: str,
        domain_response: DomainResponse,
    ) -> DomainResponse:
        if agent_name in {"InteractionAgent", "SearchKnowledgeAgent"}:
            return domain_response
        text = domain_response.assistant_text
        if not text:
            return domain_response

        system_prompt = (
            "You are HabitaLife's hospitality concierge response polisher. "
            "Rewrite the draft into warm, concise guest-facing language. "
            "Preserve facts, never invent policies, prices, or availability, "
            "and keep the answer to one or two short sentences."
        )
        user_prompt = f"Agent: {agent_name}\nDraft response: {text}"

        try:
            generation = await self._llm_provider.generate_text(system_prompt, user_prompt)
        except LLMProviderError:
            return domain_response

        polished_text = generation.text.strip()
        if "Draft response:" in polished_text:
            polished_text = polished_text.split("Draft response:", maxsplit=1)[-1].strip()
        return domain_response.model_copy(update={"assistant_text": polished_text or text})

    def _build_response(
        self,
        *,
        request: RespondRequest,
        plan_primary: str,
        intent_primary: str,
        confidence: float,
        domain_response: DomainResponse,
        secondary_intents: list[str] | None = None,
        errors: list[ErrorDetail] | None = None,
    ) -> RespondResponse:
        return RespondResponse(
            request_id=request.request_id,
            response_type=domain_response.response_type,
            intent=IntentClassification(
                primary=intent_primary,
                secondary=secondary_intents or [],
                confidence=confidence,
            ),
            assistant_message=AssistantMessage(content=domain_response.assistant_text)
            if domain_response.assistant_text
            else None,
            proposals=domain_response.proposals,
            handover=domain_response.handover,
            routing={"primary_agent": plan_primary, "confidence": confidence},
            errors=errors or [],
        )

    def _clarification_update(
        self,
        intent: str,
        agent_name: str,
    ) -> DialogueUpdate | None:
        if intent == "booking_search":
            return DialogueUpdate(
                active_intent="booking_search",
                active_agent=agent_name,
                missing_fields=["check_in_date", "check_out_date"],
            )
        if intent == "booking_lookup":
            return DialogueUpdate(
                active_intent="booking_lookup",
                active_agent=agent_name,
                missing_fields=["booking_id"],
            )
        if intent == "check_in_readiness":
            return DialogueUpdate(
                active_intent="check_in_readiness",
                active_agent=agent_name,
                missing_fields=["booking_id"],
            )
        return None
