"""Tests for the terminal chat state helpers."""

from __future__ import annotations

from agentic_intelligence_systems.cli.state import ChatState, parse_tools


def test_chat_state_builds_request_with_context():
    state = ChatState(
        resort_id="resort_1",
        booking_id="booking_1",
        room_id="room_1",
        booking_status="checked_in",
    )

    request = state.build_request("Please send extra towels.")

    assert request.booking_context
    assert request.booking_context.resort_id == "resort_1"
    assert request.booking_context.booking_id == "booking_1"
    assert request.booking_context.room_id == "room_1"
    assert request.policy_context.allowed_tool_names
    assert request.message.content == "Please send extra towels."


def test_parse_tools_supports_all_and_none():
    assert "create_booking" in parse_tools("all")
    assert parse_tools("none") == []
    assert parse_tools("create_booking,create_service_request") == [
        "create_booking",
        "create_service_request",
    ]
