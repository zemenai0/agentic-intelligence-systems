"""Conversation summarization and preference signal extraction."""

from __future__ import annotations

from agentic_intelligence_systems.contracts.private_api import (
    CandidateSignal,
    MemorySnapshot,
    MemorySummarizeRequest,
    MemorySummarizeResponse,
)
from agentic_intelligence_systems.utils.helpers import truncate_text


class MemorySummarizer:
    """Summarize transcript snippets into lightweight memory outputs."""

    def summarize(self, request: MemorySummarizeRequest) -> MemorySummarizeResponse:
        contents = [message.content for message in request.messages]
        combined = " ".join(contents).strip()
        if not combined:
            combined = (
                f"No transcript text was supplied for message IDs: "
                f"{', '.join(request.message_ids) or 'none'}."
            )

        signals = self._extract_signals(combined.lower())
        snapshot = MemorySnapshot(
            scope="stay",
            summary_text=truncate_text(combined, limit=220),
            structured_memory_json={signal.key: signal.value_text for signal in signals},
            confidence=0.82 if signals else 0.58,
        )
        return MemorySummarizeResponse(
            request_id=request.request_id,
            snapshot=snapshot,
            candidate_signals=signals,
        )

    def _extract_signals(self, text: str) -> list[CandidateSignal]:
        signals: list[CandidateSignal] = []
        if "quiet" in text and ("dinner" in text or "restaurant" in text):
            signals.append(
                CandidateSignal(
                    signal_type="preference",
                    key="quiet_dining",
                    value_text="quiet dining atmosphere",
                    confidence=0.86,
                )
            )
        if "late housekeeping" in text or "housekeeping later" in text:
            signals.append(
                CandidateSignal(
                    signal_type="preference",
                    key="late_housekeeping",
                    value_text="housekeeping later in the day",
                    confidence=0.83,
                )
            )
        if "vegetarian" in text or "vegan" in text:
            signals.append(
                CandidateSignal(
                    signal_type="preference",
                    key="dietary_preference",
                    value_text="vegetarian or vegan options",
                    confidence=0.8,
                )
            )
        return signals
