"""Helpers for booking recovery and nearby-date suggestions."""

from __future__ import annotations

from datetime import date, timedelta

AVAILABILITY_EXPLORATION_PHRASES = {
    "available dates",
    "available date",
    "which day",
    "what day",
    "any day",
    "nearby dates",
    "another date",
    "other dates",
    "wider range",
    "different dates",
    "free bookings",
    "when are rooms available",
    "when does the rooms are available",
    "list available dates",
}


def build_booking_goal_summary(check_in_date: str, check_out_date: str) -> str:
    """Build a compact semantic summary for an active booking search."""

    return f"a room search from {check_in_date} to {check_out_date}"


def iter_nearby_date_ranges(
    check_in_date: str,
    check_out_date: str,
    *,
    max_offset_days: int = 7,
) -> list[tuple[str, str]]:
    """Return nearby date ranges that preserve the original stay length."""

    start = date.fromisoformat(check_in_date)
    end = date.fromisoformat(check_out_date)
    stay_length = max((end - start).days, 1)
    ranges: list[tuple[str, str]] = []
    for offset in range(1, max_offset_days + 1):
        alt_start = start + timedelta(days=offset)
        alt_end = alt_start + timedelta(days=stay_length)
        ranges.append((alt_start.isoformat(), alt_end.isoformat()))
    return ranges


def wants_availability_exploration(message: str) -> bool:
    """Return whether the user is asking for flexible booking alternatives."""

    normalized = " ".join(message.lower().split())
    return any(phrase in normalized for phrase in AVAILABILITY_EXPLORATION_PHRASES)


def iter_extended_date_ranges(
    check_in_date: str,
    check_out_date: str,
) -> list[tuple[str, str]]:
    """Return a wider set of alternative date ranges for exploration."""

    start = date.fromisoformat(check_in_date)
    end = date.fromisoformat(check_out_date)
    stay_length = max((end - start).days, 1)
    offsets = (1, 2, 3, 4, 5, 6, 7, 10, 14, 21, 28, 35)
    ranges: list[tuple[str, str]] = []
    for offset in offsets:
        alt_start = start + timedelta(days=offset)
        alt_end = alt_start + timedelta(days=stay_length)
        ranges.append((alt_start.isoformat(), alt_end.isoformat()))
    return ranges
