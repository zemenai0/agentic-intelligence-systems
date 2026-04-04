"""Natural-language date helpers for booking flows."""

from __future__ import annotations

from datetime import date, timedelta
import re


DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NIGHT_PATTERN = re.compile(r"\b(\d+)\s+night(?:s)?\b")
DAY_PATTERN = re.compile(r"\b(\d+)\s+day(?:s)?\b")
NEXT_WEEKDAY_PATTERN = re.compile(
    r"\b(?:next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
)
WEEKDAY_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
)

WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def extract_stay_dates(text: str, reference_date: date | None = None) -> list[str]:
    """Extract stay dates from ISO or simple natural language."""

    today = reference_date or date.today()
    iso_dates = DATE_PATTERN.findall(text)
    duration_days = extract_stay_duration_days(text)
    if len(iso_dates) >= 2:
        return iso_dates[:2]
    if len(iso_dates) == 1 and duration_days:
        check_in_date = iso_dates[0]
        return [check_in_date, shift_iso_date(check_in_date, duration_days)]

    anchor = _extract_anchor_date(text, today)
    if not anchor:
        return iso_dates[:1]

    if duration_days:
        return [anchor.isoformat(), (anchor + timedelta(days=duration_days)).isoformat()]
    return [anchor.isoformat()]


def extract_stay_duration_days(text: str) -> int | None:
    """Extract a stay length from natural language."""

    lowered = text.lower()
    night_match = NIGHT_PATTERN.search(lowered)
    if night_match:
        return int(night_match.group(1))
    day_match = DAY_PATTERN.search(lowered)
    if day_match:
        return int(day_match.group(1))
    return None


def shift_iso_date(iso_date: str, days: int) -> str:
    """Return a shifted ISO date."""

    return (date.fromisoformat(iso_date) + timedelta(days=days)).isoformat()


def _extract_anchor_date(text: str, reference_date: date) -> date | None:
    lowered = text.lower()
    if "today" in lowered:
        return reference_date
    if "tomorrow" in lowered:
        return reference_date + timedelta(days=1)

    next_weekday_match = NEXT_WEEKDAY_PATTERN.search(lowered)
    if next_weekday_match:
        weekday_name = next_weekday_match.group(1)
        return _next_weekday(reference_date, WEEKDAY_INDEX[weekday_name], strict=True)

    weekday_match = WEEKDAY_PATTERN.search(lowered)
    if weekday_match:
        weekday_name = weekday_match.group(1)
        return _next_weekday(reference_date, WEEKDAY_INDEX[weekday_name], strict=False)
    return None


def _next_weekday(
    reference_date: date,
    target_weekday: int,
    *,
    strict: bool,
) -> date:
    days_ahead = (target_weekday - reference_date.weekday()) % 7
    if strict or days_ahead == 0:
        days_ahead = days_ahead or 7
    return reference_date + timedelta(days=days_ahead)
