"""Booking lookup and availability guidance."""

from __future__ import annotations

from agentic_intelligence_systems.agents.interaction import DomainResponse
from agentic_intelligence_systems.agents.message_semantics import analyze_message
from agentic_intelligence_systems.agents.booking_recovery import (
    build_booking_goal_summary,
    iter_extended_date_ranges,
    iter_nearby_date_ranges,
    wants_availability_exploration,
)
from agentic_intelligence_systems.clients.backend_api import BackendAPIClient
from agentic_intelligence_systems.contracts.common import (
    BookingContext,
    Proposal,
    ResponseType,
    RiskLevel,
)
from agentic_intelligence_systems.contracts.private_api import RespondRequest
from agentic_intelligence_systems.contracts.tools import ResortCatalogItem
from agentic_intelligence_systems.orchestration.conversation_state import (
    ConversationState,
    DialogueUpdate,
    KnownService,
)
from agentic_intelligence_systems.orchestration.policies import tool_allowed
from agentic_intelligence_systems.utils.booking_inputs import (
    count_nights,
    extract_guest_counts,
    format_price_cents,
    guest_summary,
    match_resort_choice,
    match_room_choice,
)
from agentic_intelligence_systems.utils.dates import (
    extract_stay_dates,
    extract_stay_duration_days,
    shift_iso_date,
)
from agentic_intelligence_systems.utils.helpers import (
    build_idempotency_key,
    extract_booking_id,
    extract_uuid,
)


class BookingAgent:
    """Handle booking lookup and availability-oriented requests."""

    def __init__(self, backend_client: BackendAPIClient):
        self._backend_client = backend_client

    async def handle(
        self,
        request: RespondRequest,
        conversation_state: ConversationState | None = None,
    ) -> DomainResponse:
        if self._is_explicit_lookup_request(request.message.content):
            return await self._handle_lookup(request)

        state = conversation_state or ConversationState(conversation_id="booking_temp")
        signals = analyze_message(request.message.content)
        if signals.suggests_booking_search():
            state = state.model_copy(update={"active_intent": "booking_search"})
        resort = await self._resolve_resort(request, state)
        if isinstance(resort, DomainResponse):
            return resort

        request = self._request_with_resort(request, resort)
        state = state.model_copy(
            update={
                "resort_id": resort.id,
                "selected_resort_name": resort.name,
            }
        )

        adults, children = self._merged_guest_counts(request.message.content, state)

        dates = self._resolve_dates(request.message.content, conversation_state)
        if len(dates) >= 2:
            if adults is None or children is None:
                return self._build_guest_count_follow_up(state, adults, children, dates)
            return await self._handle_availability(
                request,
                resort,
                adults,
                children,
                dates,
                state,
            )
        if len(dates) == 1:
            return self._build_date_follow_up(
                state,
                adults,
                children,
                dates,
            )
        if state.active_intent in {"branch_selection", "booking_search"}:
            if (
                state.check_in_date
                and state.check_out_date
                and (adults is None or children is None)
            ):
                return self._build_guest_count_follow_up(
                    state,
                    adults,
                    children,
                    [state.check_in_date, state.check_out_date],
                )
            if (
                state.check_in_date
                and state.check_out_date
                and adults is not None
                and children is not None
                and state.availability_status != "unavailable"
            ):
                return await self._handle_availability(
                    request,
                    resort,
                    adults,
                    children,
                    [
                        state.check_in_date,
                        state.check_out_date,
                    ],
                    state,
                )
            if (
                state.availability_status == "available_options"
                and state.check_in_date
                and state.check_out_date
            ):
                return await self._handle_availability(
                    request,
                    resort,
                    adults,
                    children,
                    [
                        state.check_in_date,
                        state.check_out_date,
                    ],
                    state,
                )
            if state.availability_status == "unavailable":
                return await self._handle_unavailable_follow_up(
                    request,
                    state,
                    adults=adults or 1,
                    children=children or 0,
                    widen_search=(
                        wants_availability_exploration(request.message.content)
                        or state.retry_count >= 2
                    ),
                )
            return self._build_date_follow_up(state, adults, children, dates)
        return await self._handle_lookup(request)

    async def _handle_lookup(self, request: RespondRequest) -> DomainResponse:
        booking_id = self._resolve_booking_id(request)
        if not booking_id:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text="Please share the booking ID you want me to check.",
            )

        record = await self._backend_client.get_booking_record(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            booking_id=booking_id,
        )
        room_text = ""
        if record.room and record.room.room_number:
            room_text = f" in room {record.room.room_number}"
        assistant_text = (
            f"Booking {record.booking_id} is currently {record.status}{room_text}. "
            f"The stay runs from {record.check_in_date} to {record.check_out_date}."
        )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=assistant_text,
        )

    async def _handle_availability(
        self,
        request: RespondRequest,
        resort: ResortCatalogItem,
        adults: int,
        children: int,
        dates: list[str],
        conversation_state: ConversationState,
    ) -> DomainResponse:
        inventory = await self._backend_client.search_room_inventory(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            arguments={
                "resort_id": request.booking_context and request.booking_context.resort_id,
                "check_in_date": dates[0],
                "check_out_date": dates[1],
                "adults": adults,
                "children": children,
            },
        )
        available = [item for item in inventory if item.availability]
        if not available:
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    "I could not find available rooms for those dates. If you want, I can "
                    "check nearby dates, try a different room type, or help with another plan."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=build_booking_goal_summary(dates[0], dates[1]),
                    availability_status="unavailable",
                    retry_count=1,
                    resort_id=resort.id,
                    selected_resort_name=resort.name,
                    check_in_date=dates[0],
                    check_out_date=dates[1],
                    adults=adults,
                    children=children,
                    missing_fields=[],
                ),
            )

        assistant_text = self._build_inventory_response(available)
        selected_room = self._select_room(request, available)
        wants_booking = self._wants_booking(request.message.content)

        if not wants_booking and not selected_room:
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    f"{assistant_text} Please tell me the room number or room ID you prefer."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=build_booking_goal_summary(dates[0], dates[1]),
                    availability_status="available_options",
                    retry_count=0,
                    resort_id=resort.id,
                    selected_resort_name=resort.name,
                    check_in_date=dates[0],
                    check_out_date=dates[1],
                    adults=adults,
                    children=children,
                    missing_fields=["room_id"],
                ),
            )

        if not selected_room and len(available) > 1:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=(
                    f"{assistant_text} Please choose one room number or room ID, and I will prepare "
                    "the booking proposal."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=build_booking_goal_summary(dates[0], dates[1]),
                    availability_status="available_options",
                    retry_count=0,
                    resort_id=resort.id,
                    selected_resort_name=resort.name,
                    check_in_date=dates[0],
                    check_out_date=dates[1],
                    adults=adults,
                    children=children,
                    missing_fields=["room_id"],
                ),
            )

        top_match = selected_room or available[0]
        if not wants_booking and selected_room:
            return await self._build_selected_room_response(
                request,
                resort,
                top_match,
                adults,
                children,
                dates,
                conversation_state,
            )
        if not tool_allowed(request.policy_context, "create_booking"):
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    f"{assistant_text} Booking proposals are not enabled for this request."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=build_booking_goal_summary(dates[0], dates[1]),
                    availability_status="available_options",
                    retry_count=0,
                    resort_id=resort.id,
                    selected_resort_name=resort.name,
                    check_in_date=dates[0],
                    check_out_date=dates[1],
                    adults=adults,
                    children=children,
                    room_id=top_match.id,
                    missing_fields=[],
                ),
            )

        selected_service_name = conversation_state.selected_service_name
        selected_service_id = conversation_state.selected_service_id
        selected_service_text = ""
        if selected_service_name:
            selected_service_text = (
                f" I also included the pending add-on service {selected_service_name} in this reservation plan."
            )

        proposal = Proposal(
            tool_name="create_booking",
            action_summary=f"Book {top_match.room_type} room from {dates[0]} to {dates[1]}",
            risk_level=RiskLevel.MEDIUM_TRANSACTIONAL,
            arguments={
                "room_id": top_match.id,
                "resort_id": resort.id,
                "check_in_date": dates[0],
                "check_out_date": dates[1],
                "adults": adults,
                "children": children,
                "special_requests": (
                    f"Selected add-on service: {selected_service_name}"
                    if selected_service_name
                    else None
                ),
                "pending_service_id": selected_service_id,
                "pending_service_name": selected_service_name,
                "pending_service_scheduled_at": (
                    f"{dates[0]}T10:00:00.000Z" if selected_service_id else None
                ),
            },
            idempotency_key=build_idempotency_key(
                "booking",
                top_match.id,
                dates[0],
                dates[1],
            ),
        )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE_WITH_PROPOSALS,
            assistant_text=(
                f"{assistant_text} I can prepare that reservation now for "
                f"{guest_summary(adults, children)}.{selected_service_text}"
            ),
            proposals=[proposal],
            dialogue_update=DialogueUpdate(
                resort_id=resort.id,
                selected_resort_name=resort.name,
                check_in_date=dates[0],
                check_out_date=dates[1],
                adults=adults,
                children=children,
                room_id=top_match.id,
                goal_summary=build_booking_goal_summary(dates[0], dates[1]),
                clear_fields=[
                    "active_intent",
                    "active_agent",
                    "goal_summary",
                    "availability_status",
                    "retry_count",
                    "selected_service_id",
                    "selected_service_name",
                    "missing_fields",
                ],
            ),
        )

    async def _handle_unavailable_follow_up(
        self,
        request: RespondRequest,
        conversation_state: ConversationState,
        *,
        adults: int,
        children: int,
        widen_search: bool,
    ) -> DomainResponse:
        if not conversation_state.check_in_date or not conversation_state.check_out_date:
            return self._build_date_follow_up(
                conversation_state,
                adults,
                children,
                [],
            )

        alternatives = await self._search_alternative_availability(
            request,
            conversation_state.check_in_date,
            conversation_state.check_out_date,
            adults=adults,
            children=children,
            widen_search=widen_search,
        )
        if alternatives:
            suggestions = self._format_date_suggestions(alternatives)
            intro = (
                "I found a few wider date options that are open:"
                if widen_search
                else "I do not see rooms on your original dates, but I found nearby availability for"
            )
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    f"{intro} {suggestions}. If one of those works, I can continue from there."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=conversation_state.goal_summary
                    or build_booking_goal_summary(
                        conversation_state.check_in_date,
                        conversation_state.check_out_date,
                    ),
                    availability_status="alternative_options",
                    retry_count=0,
                    resort_id=conversation_state.resort_id,
                    selected_resort_name=conversation_state.selected_resort_name,
                    check_in_date=conversation_state.check_in_date,
                    check_out_date=conversation_state.check_out_date,
                    adults=adults,
                    children=children,
                ),
            )

        retry_count = conversation_state.retry_count + 1
        if retry_count >= 3 or widen_search:
            return DomainResponse(
                response_type=ResponseType.ASSISTANT_MESSAGE,
                assistant_text=(
                    "I checked a wider range around those dates and still do not see open rooms. "
                    "If you want, tell me a different month, a shorter stay, or a different room "
                    "type and I will search fresh."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=conversation_state.goal_summary
                    or build_booking_goal_summary(
                        conversation_state.check_in_date,
                        conversation_state.check_out_date,
                    ),
                    availability_status="unavailable",
                    retry_count=retry_count,
                    resort_id=conversation_state.resort_id,
                    selected_resort_name=conversation_state.selected_resort_name,
                    check_in_date=conversation_state.check_in_date,
                    check_out_date=conversation_state.check_out_date,
                    adults=adults,
                    children=children,
                ),
            )

        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=(
                "I still do not see nearby availability for that stay window. If you want, "
                "I can widen the search across the next few weeks, try a different room type, "
                "or start a fresh search."
            ),
            dialogue_update=DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                goal_summary=conversation_state.goal_summary
                or build_booking_goal_summary(
                    conversation_state.check_in_date,
                    conversation_state.check_out_date,
                ),
                availability_status="unavailable",
                retry_count=retry_count,
                resort_id=conversation_state.resort_id,
                selected_resort_name=conversation_state.selected_resort_name,
                check_in_date=conversation_state.check_in_date,
                check_out_date=conversation_state.check_out_date,
                adults=adults,
                children=children,
            ),
        )

    def _resolve_booking_id(self, request: RespondRequest) -> str | None:
        if request.booking_context and request.booking_context.booking_id:
            return request.booking_context.booking_id
        return extract_booking_id(request.message.content)

    def _is_explicit_lookup_request(self, message: str) -> bool:
        lowered = " ".join(message.lower().split())
        return any(
            phrase in lowered
            for phrase in {
                "check my booking",
                "check booking",
                "show my booking",
                "booking status",
                "reservation status",
            }
        )

    def _select_room(self, request: RespondRequest, available):
        if request.booking_context and request.booking_context.room_id:
            for item in available:
                if item.id == request.booking_context.room_id:
                    return item
        return match_room_choice(request.message.content, available)

    def _resolve_room_id(self, request: RespondRequest) -> str | None:
        if request.booking_context and request.booking_context.room_id:
            return request.booking_context.room_id
        return extract_uuid(request.message.content)

    def _wants_booking(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in ("book", "reserve", "take this"))

    def _build_inventory_response(self, available) -> str:
        top_matches = available[:3]
        options = ", ".join(self._format_room_option(item) for item in top_matches)
        if len(available) > len(top_matches):
            return (
                f"I found {len(available)} available room option(s). "
                f"Top matches: {options}."
            )
        return f"I found {len(available)} available room option(s): {options}."

    def _format_room_option(self, item) -> str:
        details = [f"room {item.room_number or item.id}", item.room_type]
        price_text = format_price_cents(item.rate_amount, item.currency)
        if price_text:
            details.append(f"{price_text} per night")
        if item.max_guests:
            details.append(f"up to {item.max_guests} guests")
        return " - ".join(details)

    def _resolve_dates(
        self,
        message: str,
        conversation_state: ConversationState | None,
    ) -> list[str]:
        dates = extract_stay_dates(message)
        if len(dates) >= 2 or conversation_state is None:
            return dates
        if conversation_state.active_intent != "booking_search":
            return dates
        duration_days = extract_stay_duration_days(message)
        if (
            duration_days
            and not dates
            and conversation_state.check_in_date
            and not conversation_state.check_out_date
        ):
            return [
                conversation_state.check_in_date,
                shift_iso_date(conversation_state.check_in_date, duration_days),
            ]
        if len(dates) == 1:
            if conversation_state.check_in_date and not conversation_state.check_out_date:
                return [conversation_state.check_in_date, dates[0]]
            if conversation_state.check_out_date and not conversation_state.check_in_date:
                return [dates[0], conversation_state.check_out_date]
        return dates

    def _build_date_follow_up(
        self,
        conversation_state: ConversationState,
        adults: int,
        children: int,
        dates: list[str],
    ) -> DomainResponse:
        first_missing = self._first_missing_date_field(conversation_state)
        if len(dates) == 1:
            update = DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                goal_summary=build_booking_goal_summary(
                    dates[0] if first_missing == "check_out_date" else (
                        conversation_state.check_in_date or dates[0]
                    ),
                    dates[0] if first_missing == "check_in_date" else (
                        conversation_state.check_out_date or "your selected checkout"
                    ),
                ),
                check_in_date=dates[0]
                if first_missing == "check_out_date"
                else conversation_state.check_in_date,
                check_out_date=dates[0]
                if first_missing == "check_in_date"
                else conversation_state.check_out_date,
                resort_id=conversation_state.resort_id,
                selected_resort_name=conversation_state.selected_resort_name,
                adults=adults,
                children=children,
                missing_fields=["check_out_date" if first_missing == "check_out_date" else "check_in_date"],
            )
            prompt = (
                f"Got it. Checking in on {update.check_in_date}. How long will you stay, "
                "or what checkout date would you like?"
                if first_missing == "check_out_date"
                else f"Got it. I have your checkout on {update.check_out_date}. What check-in date would you like?"
            )
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=prompt,
                dialogue_update=update,
            )
        if first_missing == "check_out_date" and conversation_state.check_in_date:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=(
                    f"I have your check-in on {conversation_state.check_in_date}. "
                    "How long will you stay, or what checkout date would you like?"
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=conversation_state.goal_summary,
                    resort_id=conversation_state.resort_id,
                    selected_resort_name=conversation_state.selected_resort_name,
                    check_in_date=conversation_state.check_in_date,
                    check_out_date=conversation_state.check_out_date,
                    adults=adults,
                    children=children,
                    missing_fields=["check_out_date"],
                ),
            )
        if first_missing == "check_in_date" and conversation_state.check_out_date:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=(
                    f"I have your checkout on {conversation_state.check_out_date}. "
                    "What check-in date would you like?"
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    goal_summary=conversation_state.goal_summary,
                    resort_id=conversation_state.resort_id,
                    selected_resort_name=conversation_state.selected_resort_name,
                    check_in_date=conversation_state.check_in_date,
                    check_out_date=conversation_state.check_out_date,
                    adults=adults,
                    children=children,
                    missing_fields=["check_in_date"],
                ),
            )
        return DomainResponse(
            response_type=ResponseType.CLARIFICATION_REQUIRED,
            assistant_text=(
                "Please share the check-in and check-out dates so I can continue the "
                "availability search."
            ),
            dialogue_update=DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                goal_summary=conversation_state.goal_summary,
                resort_id=conversation_state.resort_id,
                selected_resort_name=conversation_state.selected_resort_name,
                check_in_date=conversation_state.check_in_date,
                check_out_date=conversation_state.check_out_date,
                adults=adults,
                children=children,
                missing_fields=["check_in_date", "check_out_date"],
            ),
        )

    def _first_missing_date_field(
        self,
        conversation_state: ConversationState,
    ) -> str:
        if conversation_state.check_in_date and not conversation_state.check_out_date:
            return "check_out_date"
        if conversation_state.check_out_date and not conversation_state.check_in_date:
            return "check_in_date"
        return "check_out_date"

    async def _search_alternative_availability(
        self,
        request: RespondRequest,
        check_in_date: str,
        check_out_date: str,
        *,
        adults: int,
        children: int,
        widen_search: bool,
    ) -> list[tuple[str, str]]:
        matches: list[tuple[str, str]] = []
        ranges = (
            iter_extended_date_ranges(check_in_date, check_out_date)
            if widen_search
            else iter_nearby_date_ranges(check_in_date, check_out_date)
        )
        for alt_check_in, alt_check_out in ranges:
            inventory = await self._backend_client.search_room_inventory(
                request_id=request.request_id,
                trace_id=request.trace_id,
                actor=request.actor,
                arguments={
                    "resort_id": request.booking_context and request.booking_context.resort_id,
                    "check_in_date": alt_check_in,
                    "check_out_date": alt_check_out,
                    "adults": adults,
                    "children": children,
                },
            )
            if any(item.availability for item in inventory):
                matches.append((alt_check_in, alt_check_out))
            if len(matches) >= 4:
                break
        return matches

    def _format_date_suggestions(
        self,
        alternatives: list[tuple[str, str]],
    ) -> str:
        return ", ".join(
            f"{check_in} to {check_out}" for check_in, check_out in alternatives[:4]
        )

    async def _resolve_resort(
        self,
        request: RespondRequest,
        conversation_state: ConversationState,
    ) -> ResortCatalogItem | DomainResponse:
        if request.booking_context and request.booking_context.resort_id:
            return ResortCatalogItem(
                id=request.booking_context.resort_id,
                name=conversation_state.selected_resort_name or "selected resort",
            )
        if conversation_state.resort_id:
            return ResortCatalogItem(
                id=conversation_state.resort_id,
                name=conversation_state.selected_resort_name or "selected resort",
            )

        resorts = await self._backend_client.get_resort_catalog(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
        )
        matched = match_resort_choice(request.message.content, resorts)
        if matched:
            return matched

        if not resorts:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=(
                    "I can help with a reservation, but I need the resort branch first."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    missing_fields=["resort_id"],
                ),
            )

        branch_names = ", ".join(
            f"{resort.name} ({resort.location})" if resort.location else resort.name
            for resort in resorts[:4]
        )
        return DomainResponse(
            response_type=ResponseType.CLARIFICATION_REQUIRED,
            assistant_text=(
                "I can help with that. Please choose a resort branch first. "
                f"Available branches: {branch_names}."
            ),
            dialogue_update=DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                missing_fields=["resort_id"],
            ),
        )

    def _request_with_resort(
        self,
        request: RespondRequest,
        resort: ResortCatalogItem,
    ) -> RespondRequest:
        booking_context = request.booking_context
        if booking_context:
            booking_context = booking_context.model_copy(update={"resort_id": resort.id})
        else:
            booking_context = BookingContext(resort_id=resort.id)
        return request.model_copy(update={"booking_context": booking_context})

    def _merged_guest_counts(
        self,
        message: str,
        conversation_state: ConversationState,
    ) -> tuple[int | None, int | None]:
        extracted_adults, extracted_children = extract_guest_counts(message)
        adults = (
            extracted_adults
            if extracted_adults is not None
            else conversation_state.adults
        )
        children = (
            extracted_children
            if extracted_children is not None
            else conversation_state.children
        )
        return adults, children

    def _build_guest_count_follow_up(
        self,
        conversation_state: ConversationState,
        adults: int | None,
        children: int | None,
        dates: list[str],
    ) -> DomainResponse:
        if adults is None and children is not None:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=(
                    f"I have {children} {'child' if children == 1 else 'children'}. "
                    "How many adults should I include?"
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    resort_id=conversation_state.resort_id,
                    selected_resort_name=conversation_state.selected_resort_name,
                    check_in_date=dates[0] if len(dates) >= 1 else conversation_state.check_in_date,
                    check_out_date=dates[1] if len(dates) >= 2 else conversation_state.check_out_date,
                    children=children,
                    missing_fields=["adults"],
                ),
            )
        if adults is not None:
            return DomainResponse(
                response_type=ResponseType.CLARIFICATION_REQUIRED,
                assistant_text=(
                    f"I have {adults} adult{'s' if adults != 1 else ''}. "
                    "How many children should I include? You can say 0 children if none."
                ),
                dialogue_update=DialogueUpdate(
                    active_intent="booking_search",
                    active_agent="BookingAgent",
                    resort_id=conversation_state.resort_id,
                    selected_resort_name=conversation_state.selected_resort_name,
                    check_in_date=dates[0] if len(dates) >= 1 else conversation_state.check_in_date,
                    check_out_date=dates[1] if len(dates) >= 2 else conversation_state.check_out_date,
                    adults=adults,
                    missing_fields=["children"],
                ),
            )
        return DomainResponse(
            response_type=ResponseType.CLARIFICATION_REQUIRED,
            assistant_text=(
                "Before I check rooms, how many adults and children will be staying?"
            ),
            dialogue_update=DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                resort_id=conversation_state.resort_id,
                selected_resort_name=conversation_state.selected_resort_name,
                check_in_date=dates[0] if len(dates) >= 1 else conversation_state.check_in_date,
                check_out_date=dates[1] if len(dates) >= 2 else conversation_state.check_out_date,
                missing_fields=["adults", "children"],
            ),
        )

    async def _build_selected_room_response(
        self,
        request: RespondRequest,
        resort: ResortCatalogItem,
        room,
        adults: int,
        children: int,
        dates: list[str],
        conversation_state: ConversationState,
    ) -> DomainResponse:
        nights = count_nights(dates[0], dates[1])
        nightly_rate = format_price_cents(room.rate_amount, room.currency)
        base_total_amount = (room.rate_amount or 0) * nights
        services = await self._backend_client.get_service_catalog(
            request_id=request.request_id,
            trace_id=request.trace_id,
            actor=request.actor,
            resort_id=resort.id,
        )
        service_names = ", ".join(item.name for item in services[:3])
        known_services = [KnownService(id=item.id, name=item.name) for item in services[:5]]
        selected_service = self._selected_service_from_state(
            services,
            conversation_state,
        )
        estimated_total_amount = base_total_amount + (
            selected_service.price if selected_service and selected_service.price else 0
        )
        estimated_total = format_price_cents(
            estimated_total_amount,
            room.currency,
        )
        service_text = (
            f" Available add-on services include {service_names}."
            if service_names
            else ""
        )
        if selected_service:
            service_text += (
                f" I’ve added {selected_service.name} to the booking plan so far."
            )
        return DomainResponse(
            response_type=ResponseType.ASSISTANT_MESSAGE,
            assistant_text=(
                f"Room {room.room_number or room.id} is a {room.room_type} option at "
                f"{nightly_rate or 'the listed nightly rate'} for {guest_summary(adults, children)}. "
                f"The estimated stay total for {nights} night{'s' if nights != 1 else ''} is "
                f"{estimated_total or 'not available'}."
                f"{service_text} If you'd like to reserve it, say book this room."
            ),
            dialogue_update=DialogueUpdate(
                active_intent="booking_search",
                active_agent="BookingAgent",
                goal_summary=build_booking_goal_summary(dates[0], dates[1]),
                availability_status="available_options",
                resort_id=resort.id,
                selected_resort_name=resort.name,
                room_id=room.id,
                check_in_date=dates[0],
                check_out_date=dates[1],
                adults=adults,
                children=children,
                selected_service_id=conversation_state.selected_service_id,
                selected_service_name=conversation_state.selected_service_name,
                known_services=known_services,
                missing_fields=[],
            ),
        )

    def _selected_service_from_state(
        self,
        services,
        conversation_state: ConversationState,
    ):
        if not conversation_state.selected_service_name and not conversation_state.selected_service_id:
            return None
        for item in services:
            if (
                conversation_state.selected_service_id
                and item.id == conversation_state.selected_service_id
            ) or (
                conversation_state.selected_service_name
                and item.name == conversation_state.selected_service_name
            ):
                return item
        return None
