"""Tests for environment-driven runtime configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic_intelligence_systems.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Reset cached settings between tests."""

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_settings_uses_local_backend_default_in_development(monkeypatch):
    monkeypatch.setenv("AGENT_ENVIRONMENT", "development")
    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)

    settings = get_settings()

    assert settings.backend_base_url == "http://localhost:3000"


def test_get_settings_requires_backend_base_url_outside_development(monkeypatch):
    monkeypatch.setenv("AGENT_ENVIRONMENT", "production")
    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)

    with pytest.raises(
        RuntimeError,
        match="BACKEND_BASE_URL must be set when AGENT_ENVIRONMENT is not development.",
    ):
        get_settings()


def test_settings_rejects_loopback_backend_outside_development():
    with pytest.raises(
        ValidationError,
        match="BACKEND_BASE_URL cannot point to localhost or another loopback address outside development.",
    ):
        Settings(environment="production", backend_base_url="http://localhost:3000")
