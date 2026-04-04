"""Input parsing helpers for booking-oriented conversations."""

from __future__ import annotations

from difflib import get_close_matches
from datetime import date
import re

from agentic_intelligence_systems.contracts.tools import (
    ResortCatalogItem,
    RoomInventoryItem,
)
from agentic_intelligence_systems.utils.helpers import extract_uuid


ADULT_PATTERN = re.compile(r"\b(\d+)\s+adult(?:s)?\b")
CHILD_PATTERN = re.compile(r"\b(\d+)\s+(?:child|children|kid|kids)\b")
GUEST_PATTERN = re.compile(r"\b(\d+)\s+(?:guest|guests|people|persons)\b")
ROOM_NUMBER_PATTERN = re.compile(r"\broom\s+(\d+)\b|\b(\d{2,4})\b")


def extract_guest_counts(text: str) -> tuple[int | None, int | None]:
    """Extract adults and children from free text."""

    lowered = text.lower()
    adults = _extract_count(ADULT_PATTERN, lowered)
    children = _extract_count(CHILD_PATTERN, lowered)
    if adults is None and "just me" in lowered:
        adults = 1
    if adults is None and children is None:
        total_guests = _extract_count(GUEST_PATTERN, lowered)
        if total_guests is not None:
            adults = total_guests
            children = 0
    return adults, children


def match_resort_choice(
    text: str,
    resorts: list[ResortCatalogItem],
) -> ResortCatalogItem | None:
    """Return the resort referenced in the message, if any."""

    lowered = text.lower()
    normalized = _normalize_text(text)
    for resort in resorts:
        if resort.id.lower() in lowered:
            return resort
    exact_name_matches = [resort for resort in resorts if resort.name.lower() in lowered]
    if len(exact_name_matches) == 1:
        return exact_name_matches[0]
    location_matches = [
        resort
        for resort in resorts
        if resort.location and resort.location.lower() in lowered
    ]
    if len(location_matches) == 1:
        return location_matches[0]
    candidates: dict[str, ResortCatalogItem] = {}
    for resort in resorts:
        variants = {
            _normalize_text(resort.name),
            _normalize_text(f"{resort.name} {resort.location or ''}"),
            _normalize_text(f"{resort.name} ({resort.location or ''})"),
        }
        for variant in variants:
            if variant:
                candidates[variant] = resort
                if variant in normalized:
                    return resort
    fuzzy_match = get_close_matches(normalized, candidates.keys(), n=1, cutoff=0.72)
    if fuzzy_match:
        return candidates[fuzzy_match[0]]
    return None


def match_room_choice(
    text: str,
    rooms: list[RoomInventoryItem],
) -> RoomInventoryItem | None:
    """Return the room referenced in the message, if any."""

    lowered = text.lower()
    room_id = extract_uuid(text)
    if room_id:
        for room in rooms:
            if room.id == room_id:
                return room
    for room in rooms:
        if room.room_number and room.room_number in lowered:
            return room

    match = ROOM_NUMBER_PATTERN.search(lowered)
    if match:
        room_number = match.group(1) or match.group(2)
        for room in rooms:
            if room.room_number == room_number:
                return room

    matching_types = [
        room for room in rooms if room.room_type.lower() in lowered
    ]
    if len(matching_types) == 1:
        return matching_types[0]
    return None


def format_price_cents(amount: float | int | None, currency: str | None) -> str | None:
    """Format a price_cents-like amount into display text."""

    if amount is None:
        return None
    return f"{currency or 'USD'} {float(amount) / 100:.2f}"


def count_nights(check_in_date: str, check_out_date: str) -> int:
    """Return the stay length in nights for ISO date strings."""

    delta = date.fromisoformat(check_out_date) - date.fromisoformat(check_in_date)
    return max(delta.days, 1)


def guest_summary(adults: int | None, children: int | None) -> str:
    """Return a readable guest summary."""

    adult_count = adults if adults is not None else 0
    child_count = children if children is not None else 0
    adult_label = "adult" if adult_count == 1 else "adults"
    child_label = "child" if child_count == 1 else "children"
    if child_count:
        return f"{adult_count} {adult_label} and {child_count} {child_label}"
    return f"{adult_count} {adult_label}"


def _extract_count(pattern: re.Pattern[str], text: str) -> int | None:
    match = pattern.search(text)
    if not match:
        return None
    return int(match.group(1))


def _normalize_text(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
