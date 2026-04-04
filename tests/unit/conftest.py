"""Shared test fixtures for the private agent service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
from agentic_intelligence_systems.api.app import create_app
from agentic_intelligence_systems.api.dependencies import ServiceContainer
from agentic_intelligence_systems.clients.llm_provider import (
    LLMProviderError,
    TextGeneration,
)
from agentic_intelligence_systems.config import Settings
from agentic_intelligence_systems.contracts.tools import (
    BookingRecord,
    CheckInReadiness,
    CurrentStayContext,
    OpenServiceRequestSummary,
    ResortCatalogItem,
    RoomInventoryItem,
    RoomSummary,
    ServiceCatalogItem,
)
from agentic_intelligence_systems.memory.summarizer import MemorySummarizer
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationStateStore,
)
from agentic_intelligence_systems.orchestration.responder import AgentResponder


class FakeBackendClient:
    """Small fake backend used for unit tests."""

    async def aclose(self) -> None:
        return None

    async def get_current_stay_context(self, **kwargs) -> CurrentStayContext:
        booking_id = kwargs["booking_id"]
        return CurrentStayContext(
            booking_id=booking_id,
            guest_user_id="user_1",
            room=RoomSummary(id="room_101", room_number="101", status="occupied"),
            stay_status="checked_in",
            open_service_requests=[
                OpenServiceRequestSummary(
                    id="sr_1",
                    type="housekeeping",
                    status="open",
                )
            ],
        )

    async def get_resort_catalog(self, **kwargs) -> list[ResortCatalogItem]:
        del kwargs
        return [
            ResortCatalogItem(
                id="resort_1",
                name="HabitaLife Water Park",
                location="Bishoftu",
                currency="USD",
                check_in_time="14:00",
                check_out_time="12:00",
                max_nights=90,
            ),
            ResortCatalogItem(
                id="resort_2",
                name="HabitaLife City Retreat",
                location="Addis Ababa",
                currency="USD",
                check_in_time="15:00",
                check_out_time="11:00",
                max_nights=30,
            ),
        ]

    async def search_room_inventory(self, **kwargs) -> list[RoomInventoryItem]:
        arguments = kwargs["arguments"]
        if (
            arguments.get("check_in_date") == "2026-07-05"
            and arguments.get("check_out_date") == "2026-07-07"
        ):
            return []
        return [
            RoomInventoryItem(
                id="room_deluxe_1",
                room_type="Deluxe",
                room_number="201",
                rate_amount=14000.0,
                currency="USD",
                floor=2,
                max_guests=3,
                bed_configuration="1 King",
                notes="Lake view",
                availability=True,
            )
        ]

    async def get_booking_record(self, **kwargs) -> BookingRecord:
        booking_id = kwargs["booking_id"]
        return BookingRecord(
            booking_id=booking_id,
            status="confirmed",
            room=RoomSummary(id="room_101", room_number="101", status="available"),
            check_in_date="2026-05-01",
            check_out_date="2026-05-03",
        )

    async def get_check_in_readiness(self, **kwargs) -> CheckInReadiness:
        booking_id = kwargs["booking_id"]
        return CheckInReadiness(
            booking_id=booking_id,
            status="eligible",
            reason="Booking is confirmed and the room is ready.",
        )

    async def get_service_catalog(self, **kwargs) -> list[ServiceCatalogItem]:
        del kwargs
        return [
            ServiceCatalogItem(
                id="svc_housekeeping",
                name="Housekeeping Support",
                category="housekeeping",
                price=0.0,
                currency="USD",
                availability="available",
            ),
            ServiceCatalogItem(
                id="svc_spa",
                name="Sunset Spa Session",
                category="spa",
                price=35.0,
                currency="USD",
                availability="available",
            ),
        ]


class FakeLLMProvider:
    """Small text provider for deterministic tests."""

    async def generate_text(self, system_prompt: str, user_prompt: str) -> TextGeneration:
        del system_prompt
        lowered = user_prompt.lower()
        if "draft response:" in lowered:
            return TextGeneration(
                text=user_prompt.split("Draft response:", maxsplit=1)[-1].strip(),
                confidence=0.5,
            )
        if "america founded" in lowered:
            return TextGeneration(
                text="The United States declared independence in 1776.",
                confidence=0.8,
            )
        if "inflation" in lowered:
            return TextGeneration(
                text="Inflation is the general rise in prices over time.",
                confidence=0.78,
            )
        if "iran war" in lowered:
            raise LLMProviderError("Provider unavailable for this request.")
        return TextGeneration(
            text="I can help with general questions as well as hospitality tasks.",
            confidence=0.5,
        )

    async def aclose(self) -> None:
        return None


def build_test_container() -> ServiceContainer:
    """Build a full service container backed by deterministic fakes."""

    settings = Settings()
    backend_client = FakeBackendClient()
    llm_provider = FakeLLMProvider()
    conversation_store = ConversationStateStore()
    recommendation_agent = RecommendationAgent(backend_client)
    search_knowledge_agent = SearchKnowledgeAgent(llm_provider)
    responder = AgentResponder(
        planner=IntentPlanner(),
        welcome_agent=WelcomeAgent(backend_client),
        interaction_agent=InteractionAgent(),
        service_request_agent=ServiceRequestAgent(backend_client),
        booking_agent=BookingAgent(backend_client),
        guest_reception_agent=GuestReceptionCheckInAgent(backend_client),
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


@pytest.fixture()
def client() -> TestClient:
    """Return a FastAPI test client with fake backend services."""

    app = create_app(container=build_test_container())
    with TestClient(app) as test_client:
        yield test_client
