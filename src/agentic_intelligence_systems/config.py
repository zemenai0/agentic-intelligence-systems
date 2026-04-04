"""Application settings."""

from __future__ import annotations

from functools import lru_cache
from ipaddress import ip_address
from os import getenv
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator
from dotenv import load_dotenv


load_dotenv()

DEVELOPMENT_ENVIRONMENTS = {"development", "dev", "test", "testing", "local"}


class Settings(BaseModel):
    """Runtime configuration loaded from the environment."""

    model_config = ConfigDict(extra="ignore")

    app_name: str = "HabitaLife Agent Service"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    backend_base_url: str = "http://localhost:3000"
    backend_timeout_seconds: float = 8.0
    backend_auth_mode: str = "none"
    backend_api_key: str | None = None
    backend_service_token: str | None = None
    backend_session_cookie: str | None = None
    llm_provider: str = "deterministic"
    llm_timeout_seconds: float = 15.0
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    gemini_model: str = "gemini-flash-latest"
    default_language: str = "en"
    request_header_name: str = "x-request-id"
    trace_header_name: str = "x-trace-id"
    service_version: str = Field(default="0.1.0")

    @model_validator(mode="after")
    def validate_backend_base_url(self) -> Settings:
        """Reject invalid or unsafe backend targets for the current environment."""

        parsed = urlparse(self.backend_base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("BACKEND_BASE_URL must be an absolute URL.")
        if (
            self.environment.lower() not in DEVELOPMENT_ENVIRONMENTS
            and _is_loopback_host(parsed.hostname)
        ):
            raise ValueError(
                "BACKEND_BASE_URL cannot point to localhost or another loopback address "
                "outside development."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the current process."""

    environment = getenv("AGENT_ENVIRONMENT", "development")
    backend_base_url = getenv("BACKEND_BASE_URL")
    if backend_base_url is None:
        if environment.lower() in DEVELOPMENT_ENVIRONMENTS:
            backend_base_url = "http://localhost:3000"
        else:
            raise RuntimeError(
                "BACKEND_BASE_URL must be set when AGENT_ENVIRONMENT is not development."
            )
    gemini_api_key = getenv("GEMINI_API_KEY")
    llm_provider = getenv(
        "LLM_PROVIDER",
        "gemini" if gemini_api_key else "deterministic",
    )
    return Settings(
        app_name=getenv("AGENT_APP_NAME", "HabitaLife Agent Service"),
        environment=environment,
        host=getenv("AGENT_HOST", "0.0.0.0"),
        port=int(getenv("AGENT_PORT", "8000")),
        log_level=getenv("AGENT_LOG_LEVEL", "INFO"),
        backend_base_url=backend_base_url,
        backend_timeout_seconds=float(getenv("BACKEND_TIMEOUT_SECONDS", "8.0")),
        backend_auth_mode=getenv("BACKEND_AUTH_MODE", "none"),
        backend_api_key=getenv("BACKEND_API_KEY"),
        backend_service_token=getenv("BACKEND_SERVICE_TOKEN"),
        backend_session_cookie=getenv("BACKEND_SESSION_COOKIE"),
        llm_provider=llm_provider,
        llm_timeout_seconds=float(getenv("LLM_TIMEOUT_SECONDS", "15.0")),
        gemini_api_key=gemini_api_key,
        gemini_base_url=getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"
        ),
        gemini_model=getenv("GEMINI_MODEL", "gemini-flash-latest"),
        default_language=getenv("DEFAULT_LANGUAGE", "en"),
        request_header_name=getenv("REQUEST_HEADER_NAME", "x-request-id"),
        trace_header_name=getenv("TRACE_HEADER_NAME", "x-trace-id"),
        service_version=getenv("SERVICE_VERSION", "0.1.0"),
    )


def _is_loopback_host(hostname: str | None) -> bool:
    """Return whether the given hostname resolves to a loopback target."""

    if hostname is None:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False
