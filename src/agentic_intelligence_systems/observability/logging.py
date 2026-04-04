"""Logging configuration for the agent service."""

from __future__ import annotations

import logging

from agentic_intelligence_systems.observability.context import (
    get_request_id,
    get_trace_id,
)


class RequestContextFilter(logging.Filter):
    """Inject request metadata into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.trace_id = get_trace_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure application logging once."""

    root_logger = logging.getLogger()
    if any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        root_logger.setLevel(level.upper())
        return

    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s/%(trace_id)s] %(name)s: %(message)s"
        )
    )
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""

    return logging.getLogger(name)
