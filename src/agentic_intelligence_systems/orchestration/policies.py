"""Policy helpers for proposal-safe orchestration."""

from __future__ import annotations

from agentic_intelligence_systems.contracts.common import ErrorDetail, PolicyContext


def validate_policy_context(policy_context: PolicyContext | None) -> ErrorDetail | None:
    """Return a stable error when policy context is missing."""

    if policy_context is None:
        return ErrorDetail(
            code="policy_context_missing",
            message="Policy context is required for respond requests.",
        )
    return None


def tool_allowed(policy_context: PolicyContext | None, tool_name: str) -> bool:
    """Check whether a tool is allowed for the current request."""

    if policy_context is None:
        return False
    return tool_name in policy_context.allowed_tool_names
