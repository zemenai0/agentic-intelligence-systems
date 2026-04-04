"""Request-scoped context storage."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4


_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")


def set_request_context(
    request_id: str | None = None,
    trace_id: str | None = None,
) -> tuple[str, str]:
    """Set request context variables and return the active values."""

    active_request_id = request_id or f"req_{uuid4().hex}"
    active_trace_id = trace_id or active_request_id.replace("req_", "trace_", 1)
    _request_id.set(active_request_id)
    _trace_id.set(active_trace_id)
    return active_request_id, active_trace_id


def get_request_id() -> str:
    """Return the current request ID."""

    return _request_id.get()


def get_trace_id() -> str:
    """Return the current trace ID."""

    return _trace_id.get()
