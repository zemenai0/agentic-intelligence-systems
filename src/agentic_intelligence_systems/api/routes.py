"""HTTP routes for the private agent service."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agentic_intelligence_systems.api.dependencies import (
    ServiceContainer,
    get_container,
    get_memory_summarizer,
    get_recommendation_agent,
    get_responder,
    get_sentiment_agent,
)
from agentic_intelligence_systems.agents.recommendation import RecommendationAgent
from agentic_intelligence_systems.agents.sentiment import SentimentAgent
from agentic_intelligence_systems.contracts.private_api import (
    MemorySummarizeRequest,
    MemorySummarizeResponse,
    RecommendRequest,
    RecommendResponse,
    RespondRequest,
    RespondResponse,
    SentimentRequest,
    SentimentResponse,
)
from agentic_intelligence_systems.memory.summarizer import MemorySummarizer
from agentic_intelligence_systems.orchestration.responder import AgentResponder


router = APIRouter()


@router.get("/health")
async def health(container: ServiceContainer = Depends(get_container)) -> dict[str, str]:
    """Return a minimal service health payload."""

    return {
        "status": "ok",
        "service": container.settings.app_name,
        "version": container.settings.service_version,
    }


@router.post("/internal/agent/respond", response_model=RespondResponse)
async def respond(
    payload: RespondRequest,
    responder: AgentResponder = Depends(get_responder),
) -> RespondResponse:
    """Handle the main conversational agent flow."""

    return await responder.respond(payload)


@router.post("/internal/agent/recommend", response_model=RecommendResponse)
async def recommend(
    payload: RecommendRequest,
    recommendation_agent: RecommendationAgent = Depends(get_recommendation_agent),
) -> RecommendResponse:
    """Return ranked recommendations."""

    return await recommendation_agent.recommend(payload)


@router.post("/internal/agent/sentiment/score", response_model=SentimentResponse)
async def score_sentiment(
    payload: SentimentRequest,
    sentiment_agent: SentimentAgent = Depends(get_sentiment_agent),
) -> SentimentResponse:
    """Score message sentiment and risk."""

    return sentiment_agent.score(payload)


@router.post("/internal/agent/memory/summarize", response_model=MemorySummarizeResponse)
async def summarize_memory(
    payload: MemorySummarizeRequest,
    memory_summarizer: MemorySummarizer = Depends(get_memory_summarizer),
) -> MemorySummarizeResponse:
    """Summarize transcript snippets into memory outputs."""

    return memory_summarizer.summarize(payload)
