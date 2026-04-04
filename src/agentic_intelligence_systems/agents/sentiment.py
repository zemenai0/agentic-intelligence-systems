"""Heuristic sentiment scoring for service recovery."""

from __future__ import annotations

from agentic_intelligence_systems.contracts.private_api import (
    RiskAssessment,
    SentimentRequest,
    SentimentResponse,
    SentimentScore,
)


NEGATIVE_WORDS = {"angry", "terrible", "bad", "hot", "broken", "nobody", "late", "dirty"}
POSITIVE_WORDS = {"great", "thank", "helpful", "perfect", "excellent", "love"}


class SentimentAgent:
    """Score message tone and handover risk."""

    def score(self, request: SentimentRequest) -> SentimentResponse:
        lowered = request.message.content.lower()
        score = 0.0
        score -= sum(0.2 for word in NEGATIVE_WORDS if word in lowered)
        score += sum(0.12 for word in POSITIVE_WORDS if word in lowered)
        score = max(-1.0, min(1.0, score))

        if score <= -0.55:
            label = "negative"
            severity = "high"
        elif score < -0.15:
            label = "mixed_negative"
            severity = "medium"
        elif score >= 0.2:
            label = "positive"
            severity = "low"
        else:
            label = "neutral"
            severity = "low"

        return SentimentResponse(
            request_id=request.request_id,
            sentiment=SentimentScore(label=label, score=score),
            risk=RiskAssessment(
                severity=severity,
                handover_required=severity == "high",
            ),
        )
