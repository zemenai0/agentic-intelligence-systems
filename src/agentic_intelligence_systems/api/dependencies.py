"""Dependency wiring for the FastAPI service."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from agentic_intelligence_systems.agents.booking import BookingAgent
from agentic_intelligence_systems.agents.guest_reception import (
    GuestReceptionCheckInAgent,
)
from agentic_intelligence_systems.agents.interaction import InteractionAgent
from agentic_intelligence_systems.agents.planner import IntentPlanner
from agentic_intelligence_systems.agents.recommendation import RecommendationAgent
from agentic_intelligence_systems.agents.search_knowledge import SearchKnowledgeAgent
from agentic_intelligence_systems.agents.sentiment import SentimentAgent
from agentic_intelligence_systems.agents.service_request import ServiceRequestAgent
from agentic_intelligence_systems.agents.welcome import WelcomeAgent
from agentic_intelligence_systems.clients.backend_api import BackendAPIClient
from agentic_intelligence_systems.clients.llm_provider import LLMProvider, build_llm_provider
from agentic_intelligence_systems.config import Settings
from agentic_intelligence_systems.memory.summarizer import MemorySummarizer
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationStateStore,
)
from agentic_intelligence_systems.orchestration.responder import AgentResponder


@dataclass(slots=True)
class ServiceContainer:
    """Runtime dependency container."""

    settings: Settings
    backend_client: BackendAPIClient
    llm_provider: LLMProvider
    conversation_store: ConversationStateStore
    responder: AgentResponder
    recommendation_agent: RecommendationAgent
    sentiment_agent: SentimentAgent
    memory_summarizer: MemorySummarizer

    async def aclose(self) -> None:
        """Close any owned network clients."""

        await self.backend_client.aclose()
        await self.llm_provider.aclose()


def build_service_container(settings: Settings) -> ServiceContainer:
    """Assemble runtime services from the configured dependencies."""

    backend_client = BackendAPIClient(settings)
    llm_provider = build_llm_provider(settings)
    conversation_store = ConversationStateStore()
    interaction_agent = InteractionAgent()
    planner = IntentPlanner()
    service_request_agent = ServiceRequestAgent(backend_client)
    booking_agent = BookingAgent(backend_client)
    guest_reception_agent = GuestReceptionCheckInAgent(backend_client)
    recommendation_agent = RecommendationAgent(backend_client)
    search_knowledge_agent = SearchKnowledgeAgent(llm_provider)
    welcome_agent = WelcomeAgent(backend_client)
    responder = AgentResponder(
        planner=planner,
        welcome_agent=welcome_agent,
        interaction_agent=interaction_agent,
        service_request_agent=service_request_agent,
        booking_agent=booking_agent,
        guest_reception_agent=guest_reception_agent,
        recommendation_agent=recommendation_agent,
        search_knowledge_agent=search_knowledge_agent,
        llm_provider=llm_provider,
        conversation_store=conversation_store,
    )
    return ServiceContainer(
        settings=settings,
        backend_client=backend_client,
        llm_provider=llm_provider,
        conversation_store=conversation_store,
        responder=responder,
        recommendation_agent=recommendation_agent,
        sentiment_agent=SentimentAgent(),
        memory_summarizer=MemorySummarizer(),
    )


def get_container(request: Request) -> ServiceContainer:
    """Return the application service container."""

    return request.app.state.container


def get_responder(request: Request) -> AgentResponder:
    """Return the main conversational responder."""

    return get_container(request).responder


def get_recommendation_agent(request: Request) -> RecommendationAgent:
    """Return the recommendation agent."""

    return get_container(request).recommendation_agent


def get_sentiment_agent(request: Request) -> SentimentAgent:
    """Return the sentiment scoring service."""

    return get_container(request).sentiment_agent


def get_memory_summarizer(request: Request) -> MemorySummarizer:
    """Return the memory summarizer."""

    return get_container(request).memory_summarizer
