"""Provider abstraction and Gemini implementation."""

from __future__ import annotations

from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from agentic_intelligence_systems.config import Settings


class TextGeneration(BaseModel):
    """Simple provider response model."""

    model_config = ConfigDict(extra="forbid")

    text: str
    confidence: float = Field(default=0.4, ge=0.0, le=1.0)


class LLMProvider(Protocol):
    """Minimal interface used by the runtime."""

    async def generate_text(self, system_prompt: str, user_prompt: str) -> TextGeneration:
        ...

    async def aclose(self) -> None:
        ...


class LLMProviderError(RuntimeError):
    """Raised when a provider request or response cannot be used."""


class DeterministicLLMProvider:
    """Fallback provider used until a real model is configured."""

    async def generate_text(self, system_prompt: str, user_prompt: str) -> TextGeneration:
        del system_prompt
        return TextGeneration(text=user_prompt.strip(), confidence=0.4)

    async def aclose(self) -> None:
        """Close any owned resources."""

        return None


class GeminiLLMProvider:
    """Gemini REST client using the generateContent endpoint."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        if not settings.gemini_api_key:
            raise LLMProviderError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")

        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.gemini_base_url,
            timeout=settings.llm_timeout_seconds,
        )

    async def generate_text(self, system_prompt: str, user_prompt: str) -> TextGeneration:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {"responseMimeType": "text/plain"},
        }
        if system_prompt.strip():
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt.strip()}]
            }

        try:
            response = await self._client.post(
                f"/v1beta/models/{self._settings.gemini_model}:generateContent",
                headers={
                    "content-type": "application/json",
                    "x-goog-api-key": self._settings.gemini_api_key,
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError("Gemini request failed.") from exc

        text = self._extract_text(response.json())
        return TextGeneration(text=text, confidence=0.78)

    async def aclose(self) -> None:
        """Close any owned HTTP client."""

        if self._owns_client:
            await self._client.aclose()

    def _extract_text(self, payload: dict) -> str:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                text = part.get("text")
                if text and text.strip():
                    return text.strip()

        prompt_feedback = payload.get("promptFeedback") or {}
        block_reason = prompt_feedback.get("blockReason")
        if block_reason:
            raise LLMProviderError(f"Gemini blocked the prompt: {block_reason}.")
        raise LLMProviderError("Gemini returned no text candidates.")


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Create the configured provider."""

    if settings.llm_provider == "gemini":
        return GeminiLLMProvider(settings)
    return DeterministicLLMProvider()
