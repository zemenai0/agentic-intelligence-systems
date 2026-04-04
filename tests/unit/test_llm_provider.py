"""Tests for the Gemini provider adapter."""

from __future__ import annotations

import json

import httpx
import pytest

from agentic_intelligence_systems.clients.llm_provider import (
    GeminiLLMProvider,
    LLMProviderError,
)
from agentic_intelligence_systems.config import Settings


@pytest.mark.asyncio
async def test_gemini_provider_builds_request_and_reads_text():
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))

        assert request.url.path.endswith(":generateContent")
        assert request.headers["x-goog-api-key"] == "test-key"
        assert payload["system_instruction"]["parts"][0]["text"] == "system prompt"
        assert payload["contents"][0]["parts"][0]["text"] == "draft response"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Polished guest-facing response."}]
                        }
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com",
    )
    provider = GeminiLLMProvider(
        Settings(
            llm_provider="gemini",
            gemini_api_key="test-key",
        ),
        http_client=client,
    )

    generation = await provider.generate_text("system prompt", "draft response")

    assert generation.text == "Polished guest-facing response."
    await client.aclose()


@pytest.mark.asyncio
async def test_gemini_provider_raises_when_prompt_is_blocked():
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"promptFeedback": {"blockReason": "SAFETY"}},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com",
    )
    provider = GeminiLLMProvider(
        Settings(
            llm_provider="gemini",
            gemini_api_key="test-key",
        ),
        http_client=client,
    )

    with pytest.raises(LLMProviderError):
        await provider.generate_text("system prompt", "draft response")

    await client.aclose()
