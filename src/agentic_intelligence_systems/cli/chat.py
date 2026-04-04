"""Interactive terminal chat for the HabitaLife agent runtime."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from agentic_intelligence_systems.api.dependencies import build_service_container
from agentic_intelligence_systems.cli.state import ChatState, parse_tools
from agentic_intelligence_systems.clients.proposal_execution import execute_proposal
from agentic_intelligence_systems.config import get_settings
from agentic_intelligence_systems.contracts.common import ActorType, Proposal
from agentic_intelligence_systems.utils.booking_inputs import format_price_cents


def main() -> None:
    asyncio.run(run_chat())


async def run_chat() -> None:
    settings = get_settings()
    state = ChatState(conversation_id=f"terminal_{uuid.uuid4().hex[:8]}")
    container = build_service_container(settings)
    configure_chat_logging()
    print("HabitaLife terminal chat")
    print("Type /help for commands. Type /quit to exit.")
    print(f"Backend: {settings.backend_base_url}")
    try:
        while True:
            raw = input("\nyou> ").strip()
            if not raw:
                continue
            if raw.startswith("/"):
                if await handle_command(state, container, raw):
                    continue
                break
            request = state.build_request(raw)
            response = await container.responder.respond(request)
            state.latest_proposals = list(response.proposals)
            if await maybe_execute_proposals(container, state, raw, response.proposals):
                continue
            render_response(response)
    finally:
        await container.aclose()


def configure_chat_logging() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def handle_command(state: ChatState, container, raw: str) -> bool:
    command, _, value = raw.partition(" ")
    value = value.strip()

    if command in {"/quit", "/exit"}:
        return False
    if command == "/help":
        print_help()
        return True
    if command in {"/show", "/context"}:
        print(state.summary())
        return True
    if command == "/run":
        if not state.latest_proposals:
            print("No proposal is waiting to run.")
            return True
        try:
            index = max(int(value or "1"), 1) - 1
            proposal = state.latest_proposals[index]
        except (ValueError, IndexError):
            print("Choose a valid proposal number, for example /run 1.")
            return True
        await execute_and_render_proposal(container, state, proposal)
        return True
    if command == "/reset":
        state.booking_id = None
        state.room_id = None
        state.booking_status = None
        state.latest_proposals = []
        print("Cleared booking, room, and status context.")
        return True
    if command == "/resort":
        state.resort_id = value or None
        print(f"resort_id={state.resort_id or '-'}")
        return True
    if command == "/booking":
        state.booking_id = value or None
        print(f"booking_id={state.booking_id or '-'}")
        return True
    if command == "/room":
        state.room_id = value or None
        print(f"room_id={state.room_id or '-'}")
        return True
    if command == "/status":
        state.booking_status = value or None
        print(f"status={state.booking_status or '-'}")
        return True
    if command == "/user":
        state.user_id = value or state.user_id
        print(f"user_id={state.user_id}")
        return True
    if command == "/staff":
        state.internal_staff_id = value or None
        print(f"internal_staff_id={state.internal_staff_id or '-'}")
        return True
    if command == "/actor":
        try:
            state.actor_type = ActorType(value or "guest")
        except ValueError:
            print("actor_type must be one of: guest, staff, manager, admin")
            return True
        print(f"actor_type={state.actor_type.value}")
        return True
    if command == "/lang":
        state.language = value or state.language
        print(f"language={state.language}")
        return True
    if command == "/tools":
        state.allowed_tool_names = parse_tools(value)
        print(f"tools={', '.join(state.allowed_tool_names) or 'none'}")
        return True

    print("Unknown command. Type /help for the supported commands.")
    return True


def render_response(response, *, show_proposals: bool = True) -> None:
    if response.assistant_message:
        print(f"agent> {response.assistant_message.content}")
    if show_proposals and response.proposals:
        print("proposals>")
        for index, proposal in enumerate(response.proposals, start=1):
            print(
                f"  {index}. {proposal.tool_name}: {proposal.action_summary} "
                f"[risk={proposal.risk_level.value}]"
            )
            print(f"     args={json.dumps(proposal.arguments, ensure_ascii=True)}")
    if response.handover:
        print(
            "handover> "
            f"{response.handover.reason.value}: {response.handover.summary}"
        )
    if response.errors:
        for error in response.errors:
            print(f"error> {error.code}: {error.message}")


def print_help() -> None:
    print("Commands:")
    print("  /show                 Show current conversation context.")
    print("  /run <n>              Execute the nth pending proposal.")
    print("  /resort <id>          Set resort_id for discovery flows.")
    print("  /booking <id>         Set booking_id for stay or service flows.")
    print("  /room <id>            Set room_id for room-specific flows.")
    print("  /status <value>       Set booking status, for example checked_in.")
    print("  /user <id>            Change guest user_id.")
    print("  /actor <type>         Set actor type: guest, staff, manager, admin.")
    print("  /staff <id>           Set internal staff ID for staff flows.")
    print("  /lang <code>          Set conversation language.")
    print("  /tools <list>         Comma-separated tools, or all/none.")
    print("  /reset                Clear booking, room, and status context.")
    print("  /quit                 Exit the chat.")


async def maybe_execute_proposals(container, state: ChatState, raw: str, proposals) -> bool:
    if not should_auto_execute_confirmation(raw, proposals):
        return False
    await execute_and_render_proposal(container, state, proposals[0])
    return True


def should_auto_execute_confirmation(raw: str, proposals) -> bool:
    if len(proposals) != 1:
        return False
    proposal = proposals[0]
    if proposal.tool_name != "create_booking":
        return False
    normalized = " ".join(raw.lower().split())
    return any(
        phrase in normalized
        for phrase in {
            "book now",
            "please book now",
            "book it now",
            "book this room",
            "book the room",
            "please book the room",
            "confirm booking",
            "confirm the booking",
            "reserve this room",
            "yes book it",
        }
    )


async def execute_and_render_proposal(
    container,
    state: ChatState,
    proposal: Proposal,
) -> None:
    try:
        execution = await execute_proposal(
            container.backend_client,
            request_id=f"exec_{uuid.uuid4().hex[:8]}",
            trace_id=f"exec_trace_{uuid.uuid4().hex[:8]}",
            proposal=proposal,
        )
    except Exception as exc:
        print(f"error> execution_failed: {exc}")
        return
    state.latest_proposals = []
    if execution.booking:
        state.booking_id = execution.booking.booking_id
        state.room_id = execution.booking.room.id if execution.booking.room else state.room_id
        state.resort_id = execution.booking.resort_id or state.resort_id
        state.booking_status = execution.booking.status or state.booking_status
        print(f"agent> {_build_booking_success_message(execution)}")
        service_line = _build_service_summary_message(execution)
        if service_line:
            print(f"agent> {service_line}")
        return
    print(f"agent> Executed {execution.tool_name} successfully.")


def _build_booking_success_message(execution) -> str:
    booking = execution.booking
    room_label = "your room"
    if booking and booking.room:
        room_bits = [
            bit
            for bit in (
                f"room {booking.room.room_number}" if booking.room.room_number else None,
                booking.room.room_type.lower() if booking.room.room_type else None,
            )
            if bit
        ]
        if room_bits:
            room_label = " - ".join(room_bits)

    total_text = None
    if booking and booking.total_price_cents is not None:
        total_text = format_price_cents(booking.total_price_cents, "USD")

    if total_text:
        return (
            f"You have booked {room_label} for {total_text}. "
            f"Your booking ID is {booking.booking_id}."
        )
    return f"You have booked {room_label}. Your booking ID is {booking.booking_id}."


def _build_service_summary_message(execution) -> str | None:
    if not execution.service_name:
        return None
    if execution.service_booking_total_cents is not None:
        service_total_text = format_price_cents(
            execution.service_booking_total_cents,
            "USD",
        )
        return (
            f"Additional service booked: {execution.service_name} "
            f"for {service_total_text}."
        )
    return f"Additional requested service: {execution.service_name}."
