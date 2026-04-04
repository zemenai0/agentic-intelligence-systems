"""Semantic message analysis for planner routing."""

from __future__ import annotations

from dataclasses import dataclass
import re

from agentic_intelligence_systems.agents.open_intents import (
    OpenIntentMatch,
    detect_open_intent,
)
from agentic_intelligence_systems.utils.booking_inputs import extract_guest_counts
from agentic_intelligence_systems.utils.dates import (
    extract_stay_dates,
    extract_stay_duration_days,
)
from agentic_intelligence_systems.utils.helpers import extract_booking_id, extract_uuid


LIST_HINTS = {"what", "which", "show", "list", "current", "available"}
ACTION_HINTS = {
    "i want", "i need", "i'd like",
    "i would like", "can i", "looking for", "find me",
    "book me", "reserve",
    "can you", "could you", "please",
}

STATUS_HINTS = {"status", "ready", "confirmed", "checked in", "check in"}
BRANCH_TERMS = {"branch", "branches", "branchs", "resort", "resorts", "location"}
BOOKING_TERMS = {"book", "booking", "reservation", "reserve", "reserved"}
ROOM_TERMS = {"room", "suite", "deluxe", "standard", "superior", "villa"}
STAY_TERMS = {"stay", "nights", "night", "check in", "check-in", "check out"}
SERVICE_TERMS = {"service", "services", "massage", "spa", "treatment", "session"}
SERVICE_REQUEST_TERMS = {"ac", "air conditioning", "towel", "towels", "pillow", "pillows", "blanket", 
                         "clean", "cleaning", "housekeeping", "laundry", "soap", "hot", "cold", 
                         "repair", "maintenance", "broken", "leak", "not working", "shuttle", "taxi",
                         "pickup", "dropoff"}

RECOMMENDATION_TERMS = {
    "recommend", "suggest", "restaurant",
    "dinner", "lunch", "activity",
}
CHECK_IN_TERMS = {"check in", "check-in", "arrival", "arrived", "room ready"}
FAQ_TERMS = {"wifi", "checkout", "check-out", "breakfast", "policy", "pool"}
AVAILABILITY_TERMS = {"available", "availability", "open", "free"}
EXISTING_BOOKING_PHRASES = {
    "my booking", "my reservation",
    "to my booking", "for my booking",
    "existing booking",
}
BOOKING_LOOKUP_PHRASES = {
    "check my booking", "check booking",
    "show my booking", "booking status",
    "reservation status",
}

SOFT_CONTINUATION_PHRASES = {"help", "help me", "continue", "go on", "okay", "ok", "yes", "yeah",
"yep", "sure", "please", "hello", "hi", "hey"}

ROOM_SELECTION_PATTERN = re.compile(r"\broom\s+\d+\b|\b\d{2,4}\b")


@dataclass(slots=True)
class MessageSemantics:
    # Compact semantic signals extracted from the full user message.

    normalized: str
    booking_id: str | None
    dates: list[str]
    duration_days: int | None
    adults: int | None
    children: int | None
    open_intent: OpenIntentMatch | None
    asks_question: bool
    asks_list: bool
    asks_status: bool
    wants_action: bool
    asks_availability: bool
    mentions_branch: bool
    mentions_booking: bool
    mentions_room: bool
    mentions_stay: bool
    mentions_service: bool
    mentions_service_request: bool
    mentions_recommendation: bool
    mentions_check_in: bool
    mentions_faq: bool
    mentions_existing_booking: bool
    room_selection_hint: bool

    @property
    def booking_identifier_only(self) -> bool:
        return bool(self.booking_id and self.normalized == self.booking_id.lower())

    def suggests_check_in(self) -> bool:
        return self.mentions_check_in and (
            self.mentions_booking or self.asks_status or self.booking_id is not None
        )

    def suggests_branch_catalog(self) -> bool:
        if self.mentions_branch and (self.asks_list or self.asks_question):
            return True
        return self.normalized in {"branches", "resorts", "locations"}

    def suggests_service_catalog(self) -> bool:
        return self.mentions_service and self.asks_list

    def suggests_service_booking(self, has_known_service: bool = False) -> bool:
        if has_known_service and not self.suggests_branch_catalog():
            return True
        return (
            self.wants_action
            and self.mentions_existing_booking
            and self.mentions_service
        )

    def suggests_service_request(self) -> bool:
        return self.mentions_service_request and not self.suggests_service_booking()

    def suggests_booking_lookup(self) -> bool:
        if self.booking_id is not None:
            return True
        if _contains_phrase(self.normalized, BOOKING_LOOKUP_PHRASES):
            return True
        return (
            self.mentions_booking
            and self.asks_status
            and not self.dates
            and self.duration_days is None
        )

    def requests_booking_lookup_explicitly(self) -> bool:
        if _contains_phrase(self.normalized, BOOKING_LOOKUP_PHRASES):
            return True
        return (
            self.mentions_booking
            and self.asks_status
            and not self.dates
            and self.duration_days is None
        )

    def suggests_booking_search(self) -> bool:
        if self.booking_identifier_only:
            return False
        if self.dates or self.duration_days:
            return True
        if self.adults is not None or self.children is not None:
            return True
        if self.asks_availability and (
            self.mentions_booking or self.mentions_room or self.mentions_stay
        ):
            return True
        return self.wants_action and (
            self.mentions_booking or self.mentions_room or self.mentions_stay
        )

    def suggests_recommendation(self) -> bool:
        return self.mentions_recommendation and not self.mentions_existing_booking

    def suggests_faq(self) -> bool:
        return self.mentions_faq and self.asks_question

    def suggests_task_continuation(self) -> bool:
        if self.normalized in SOFT_CONTINUATION_PHRASES:
            return True
        if _contains_phrase(self.normalized, SOFT_CONTINUATION_PHRASES):
            return True
        if self.open_intent and self.open_intent.intent == "greeting":
            return True
        return False


def analyze_message(message: str) -> MessageSemantics:
    """Extract semantic signals from the full user message."""

    normalized = " ".join(message.lower().split())
    booking_id = extract_booking_id(message)
    dates = extract_stay_dates(message)
    duration_days = extract_stay_duration_days(message)
    adults, children = extract_guest_counts(message)
    open_intent = detect_open_intent(message)
    asks_question = normalized.endswith("?") or _starts_with_question(normalized)
    asks_list = _contains_term(normalized, {"show", "list"}) or (
        asks_question and _contains_term(normalized, LIST_HINTS)
    )
    asks_status = asks_question and _contains_term(normalized, STATUS_HINTS)
    wants_action = _contains_phrase(normalized, ACTION_HINTS)
    asks_availability = _contains_term(normalized, AVAILABILITY_TERMS)
    mentions_branch = _contains_term(normalized, BRANCH_TERMS)
    mentions_booking = _contains_term(normalized, BOOKING_TERMS)
    mentions_room = _contains_term(normalized, ROOM_TERMS)
    mentions_stay = _contains_term(normalized, STAY_TERMS) or bool(dates)
    mentions_service = _contains_term(normalized, SERVICE_TERMS)
    mentions_service_request = _contains_term(normalized, SERVICE_REQUEST_TERMS)
    mentions_recommendation = _contains_term(normalized, RECOMMENDATION_TERMS)
    mentions_check_in = _contains_term(normalized, CHECK_IN_TERMS)
    mentions_faq = _contains_term(normalized, FAQ_TERMS)
    mentions_existing_booking = _contains_phrase(normalized, EXISTING_BOOKING_PHRASES)
    room_selection_hint = bool(
        extract_uuid(message) or ROOM_SELECTION_PATTERN.search(normalized)
    )
    return MessageSemantics(
        normalized=normalized,
        booking_id=booking_id,
        dates=dates,
        duration_days=duration_days,
        adults=adults,
        children=children,
        open_intent=open_intent,
        asks_question=asks_question,
        asks_list=asks_list,
        asks_status=asks_status,
        wants_action=wants_action,
        asks_availability=asks_availability,
        mentions_branch=mentions_branch,
        mentions_booking=mentions_booking,
        mentions_room=mentions_room,
        mentions_stay=mentions_stay,
        mentions_service=mentions_service,
        mentions_service_request=mentions_service_request,
        mentions_recommendation=mentions_recommendation,
        mentions_check_in=mentions_check_in,
        mentions_faq=mentions_faq,
        mentions_existing_booking=mentions_existing_booking,
        room_selection_hint=room_selection_hint,
    )


def _contains_term(normalized: str, terms: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in terms)


def _contains_phrase(normalized: str, phrases: set[str]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def _starts_with_question(normalized: str) -> bool:
    first_word = normalized.split(" ", maxsplit=1)[0] if normalized else ""
    return first_word in {
        "who", "what", "when","where", "why", "how", "which", "can", "could", "do", "does", "did",
        "is","are",
    }
