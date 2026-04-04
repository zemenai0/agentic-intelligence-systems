"""General helpers shared across the agent runtime."""

from __future__ import annotations

import re
from hashlib import sha1


DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
BOOKING_ID_PATTERN = re.compile(r"\b(?:res|booking)_[a-zA-Z0-9_-]+\b")


def contains_any(text: str, keywords: set[str]) -> bool:
    """Return True when any keyword appears in the given text."""

    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def extract_iso_dates(text: str) -> list[str]:
    """Extract ISO-like dates from free text."""

    return DATE_PATTERN.findall(text)


def extract_booking_id(text: str) -> str | None:
    """Extract a booking-style ID or UUID from free text."""

    booking_match = BOOKING_ID_PATTERN.search(text)
    if booking_match:
        return booking_match.group(0)
    return extract_uuid(text)


def extract_uuid(text: str) -> str | None:
    """Extract a UUID from free text."""

    uuid_match = UUID_PATTERN.search(text)
    if uuid_match:
        return uuid_match.group(0)
    return None


def truncate_text(text: str, limit: int = 180) -> str:
    """Trim text without breaking readability."""

    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3].rstrip()}..."


def slugify_text(text: str) -> str:
    """Create a safe slug for idempotency keys and identifiers."""

    compact = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return compact or "request"


def build_idempotency_key(*parts: str) -> str:
    """Create a stable idempotency key from multiple string parts."""

    base = "_".join(slugify_text(part) for part in parts if part)
    digest = sha1(base.encode("utf-8")).hexdigest()[:10]
    return f"{base[:48]}_{digest}".strip("_")
