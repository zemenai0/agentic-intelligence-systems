"""Sequential dialogue tests for multi-turn context retention."""

from __future__ import annotations

from agentic_intelligence_systems.agents.booking import BookingAgent
from agentic_intelligence_systems.contracts.tools import RoomInventoryItem


def test_service_booking_keeps_context_until_date_is_filled(client):
    conversation = {
        "conversation_id": "conv_dialogue_1",
        "channel": "mobile_chat",
        "language": "en",
    }

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_1",
            "trace_id": "trace_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
            "message": {"message_id": "msg_1", "content": "What services do you have?"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_2",
            "trace_id": "trace_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
            "message": {
                "message_id": "msg_2",
                "content": "Please add Sunset Spa Session to my booking.",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"
    assert body["intent"]["primary"] == "service_booking"

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_3",
            "trace_id": "trace_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
            "message": {"message_id": "msg_3", "content": "2026-07-05"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message_with_proposals"
    assert body["proposals"][0]["tool_name"] == "create_service_booking"
    assert body["proposals"][0]["arguments"]["scheduled_at"].startswith("2026-07-05")


def test_service_booking_keeps_service_and_date_until_booking_is_filled(client):
    conversation = {
        "conversation_id": "conv_dialogue_1b",
        "channel": "mobile_chat",
        "language": "en",
    }

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_1b",
            "trace_id": "trace_1b",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_1b", "content": "What services do you have?"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_2b",
            "trace_id": "trace_2b",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_2b",
                "content": "Please add Sunset Spa Session to my booking.",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"
    assert "booking id and the preferred date" in body["assistant_message"]["content"].lower()

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_3b",
            "trace_id": "trace_3b",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_3b", "content": "2026-07-05"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"
    assert "please share the booking id" in body["assistant_message"]["content"].lower()

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_4b",
            "trace_id": "trace_4b",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_4b", "content": "booking_123"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message_with_proposals"
    assert body["proposals"][0]["tool_name"] == "create_service_booking"
    assert body["proposals"][0]["arguments"]["scheduled_at"].startswith("2026-07-05")


def test_prebooking_service_stays_inside_booking_flow(client):
    conversation = {
        "conversation_id": "conv_dialogue_prebooking_service",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_1",
            "trace_id": "trace_prebooking_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_prebooking_1",
                "content": "I need a room for 2 adults and 0 children from 2026-05-01 to 2026-05-03",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )

    selected_room = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_2",
            "trace_id": "trace_prebooking_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_prebooking_2", "content": "room 201"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )
    selected_room_body = selected_room.json()
    assert "book this room" in selected_room_body["assistant_message"]["content"].lower()

    add_service = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_3",
            "trace_id": "trace_prebooking_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_prebooking_3",
                "content": "add Sunset Spa Session",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )
    add_service_body = add_service.json()
    assert add_service_body["intent"]["primary"] == "service_booking"
    assert add_service_body["response_type"] == "assistant_message"
    assert "added sunset spa session" in add_service_body["assistant_message"]["content"].lower()

    book_room = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_4",
            "trace_id": "trace_prebooking_4",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_prebooking_4", "content": "please book the room"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )
    book_room_body = book_room.json()
    assert book_room_body["intent"]["primary"] == "booking_search"
    assert book_room_body["response_type"] == "assistant_message_with_proposals"
    assert book_room_body["proposals"][0]["tool_name"] == "create_booking"
    assert "sunset spa session" in book_room_body["assistant_message"]["content"].lower()


def test_prebooking_service_catalog_does_not_break_room_booking_flow(client):
    conversation = {
        "conversation_id": "conv_dialogue_prebooking_service_catalog",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_catalog_1",
            "trace_id": "trace_prebooking_catalog_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_prebooking_catalog_1",
                "content": "I need a room for 2 adults and 0 children from 2026-05-01 to 2026-05-03",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_catalog_2",
            "trace_id": "trace_prebooking_catalog_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_prebooking_catalog_2", "content": "room 201"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )

    service_catalog = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_catalog_3",
            "trace_id": "trace_prebooking_catalog_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_prebooking_catalog_3",
                "content": "what services do you have?",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )
    assert "sunset spa session" in service_catalog.json()["assistant_message"]["content"].lower()

    add_service = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_catalog_4",
            "trace_id": "trace_prebooking_catalog_4",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_prebooking_catalog_4",
                "content": "add Sunset Spa Session",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )
    add_service_body = add_service.json()
    assert add_service_body["response_type"] == "assistant_message"
    assert "added sunset spa session" in add_service_body["assistant_message"]["content"].lower()

    book_room = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_prebooking_catalog_5",
            "trace_id": "trace_prebooking_catalog_5",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_prebooking_catalog_5", "content": "book this room"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking", "create_service_booking"],
            },
        },
    )
    book_room_body = book_room.json()
    assert book_room_body["intent"]["primary"] == "booking_search"
    assert book_room_body["response_type"] == "assistant_message_with_proposals"
    assert book_room_body["proposals"][0]["tool_name"] == "create_booking"
    assert "sunset spa session" in book_room_body["assistant_message"]["content"].lower()


def test_service_request_keeps_context_until_booking_id_is_filled(client):
    conversation = {
        "conversation_id": "conv_dialogue_2",
        "channel": "mobile_chat",
        "language": "en",
    }

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_4",
            "trace_id": "trace_4",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_4", "content": "Please send extra towels."},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_request"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"
    assert body["intent"]["primary"] == "service_request"

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_5",
            "trace_id": "trace_5",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_5", "content": "booking_123"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_request"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message_with_proposals"
    assert body["proposals"][0]["tool_name"] == "create_service_request"


def test_booking_search_keeps_context_for_single_date_follow_up(client):
    conversation = {
        "conversation_id": "conv_dialogue_3",
        "channel": "mobile_chat",
        "language": "en",
    }

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_6",
            "trace_id": "trace_6",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_6", "content": "I need booking help."},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_7",
            "trace_id": "trace_7",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_7", "content": "2026-07-05"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"
    assert "how long will you stay" in body["assistant_message"]["content"].lower()


def test_explicit_booking_lookup_overrides_stale_booking_search_state(client):
    conversation = {
        "conversation_id": "conv_dialogue_lookup_override",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_lookup_override_1",
            "trace_id": "trace_lookup_override_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_lookup_override_1",
                "content": "I want a room from 2026-05-01 to 2026-05-03",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_lookup_override_2",
            "trace_id": "trace_lookup_override_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_lookup_override_2", "content": "2 adults"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_lookup_override_3",
            "trace_id": "trace_lookup_override_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_lookup_override_3",
                "content": "my booking id is booking_123 check my booking",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    body = response.json()
    assert body["intent"]["primary"] == "booking_lookup"
    assert "booking booking_123 is currently confirmed" in body["assistant_message"]["content"].lower()


def test_ac_maintenance_routes_to_service_request(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_ac_1",
            "trace_id": "trace_ac_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_dialogue_ac_1",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_ac_1", "content": "the AC is not working"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_service_request"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "service_request"
    assert body["response_type"] == "clarification_required"
    assert "please share the booking id" in body["assistant_message"]["content"].lower()


def test_inventory_response_says_top_matches_when_more_rooms_exist():
    agent = BookingAgent(backend_client=None)
    rooms = [
        RoomInventoryItem(id="room_1", room_type="Suite", room_number="301", rate_amount=45000, currency="USD", max_guests=4),
        RoomInventoryItem(id="room_2", room_type="Superior", room_number="202", rate_amount=28000, currency="USD", max_guests=2),
        RoomInventoryItem(id="room_3", room_type="Deluxe", room_number="201", rate_amount=32000, currency="USD", max_guests=3),
        RoomInventoryItem(id="room_4", room_type="Standard", room_number="100", rate_amount=25000, currency="USD", max_guests=3),
    ]

    text = agent._build_inventory_response(rooms)

    assert "i found 4 available room option(s). top matches:" in text.lower()


def test_booking_lookup_state_does_not_hijack_new_booking_search(client):
    conversation = {
        "conversation_id": "conv_dialogue_lookup_to_new_booking",
        "channel": "mobile_chat",
        "language": "en",
    }

    lookup = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_lookup_to_new_booking_1",
            "trace_id": "trace_lookup_to_new_booking_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
            "message": {
                "message_id": "msg_lookup_to_new_booking_1",
                "content": "check my booking",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    assert lookup.json()["intent"]["primary"] == "booking_lookup"

    new_booking = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_lookup_to_new_booking_2",
            "trace_id": "trace_lookup_to_new_booking_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
            "message": {
                "message_id": "msg_lookup_to_new_booking_2",
                "content": "I want to book second room",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = new_booking.json()
    assert body["intent"]["primary"] == "booking_search"
    assert body["response_type"] == "clarification_required"
    assert "check-in and check-out dates" in body["assistant_message"]["content"].lower()


def test_greeting_plus_can_i_book_routes_to_booking_search(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_can_i_book",
            "trace_id": "trace_can_i_book",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_dialogue_can_i_book",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
            "message": {
                "message_id": "msg_can_i_book",
                "content": "hello can i book",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"


def test_booking_supports_natural_language_date_follow_up(client):
    conversation = {
        "conversation_id": "conv_dialogue_4",
        "channel": "mobile_chat",
        "language": "en",
    }

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_8",
            "trace_id": "trace_8",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_8",
                "content": "I want to book a room for tomorrow",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "clarification_required"
    assert "how long will you stay" in body["assistant_message"]["content"].lower()


def test_booking_fills_duration_from_follow_up_message(client):
    conversation = {
        "conversation_id": "conv_dialogue_4b",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_8b_1",
            "trace_id": "trace_8b_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_8b_1",
                "content": "I want to book a room for tomorrow",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_8b_2",
            "trace_id": "trace_8b_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_8b_2", "content": "2 days"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert "how many adults and children" in body["assistant_message"]["content"].lower()

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_8b_3",
            "trace_id": "trace_8b_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_8b_3",
                "content": "2 adults and 0 children",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert "available room option" in body["assistant_message"]["content"].lower()


def test_active_booking_help_keeps_slot_filling(client):
    conversation = {
        "conversation_id": "conv_dialogue_4c",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_8c_1",
            "trace_id": "trace_8c_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_8c_1",
                "content": "I want to book a room for tomorrow",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_8c_2",
            "trace_id": "trace_8c_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_8c_2", "content": "can you help me"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert "how long will you stay" in body["assistant_message"]["content"].lower()


def test_booking_unavailable_flow_suggests_nearby_dates(client):
    conversation = {
        "conversation_id": "conv_dialogue_5",
        "channel": "mobile_chat",
        "language": "en",
    }

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_9",
            "trace_id": "trace_9",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_9",
                "content": "I want a booking for 2 adults and 0 children from 2026-07-05 to 2026-07-07",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert "nearby dates" in body["assistant_message"]["content"].lower()

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_10",
            "trace_id": "trace_10",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_10",
                "content": "when are rooms available then",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert "date options" in body["assistant_message"]["content"].lower()


def test_booking_unavailable_flow_handles_available_dates_request(client):
    conversation = {
        "conversation_id": "conv_dialogue_6",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_11",
            "trace_id": "trace_11",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_11",
                "content": "I want a booking for 2 adults and 0 children from 2026-07-05 to 2026-07-07",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_12",
            "trace_id": "trace_12",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_12",
                "content": "can you list available dates",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert "date options" in body["assistant_message"]["content"].lower()
