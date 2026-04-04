"""Tests for the private API surface."""

from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "HabitaLife Agent Service"


def test_respond_creates_service_request_proposal(client):
    payload = {
        "request_id": "req_1",
        "trace_id": "trace_1",
        "actor": {"actor_type": "guest", "user_id": "user_1"},
        "conversation": {
            "conversation_id": "conv_1",
            "channel": "mobile_chat",
            "language": "en",
        },
        "booking_context": {
            "booking_id": "booking_123",
            "room_id": "room_101",
            "resort_id": "resort_1",
            "status": "checked_in",
        },
        "message": {"message_id": "msg_1", "content": "Please send extra towels."},
        "policy_context": {
            "proposal_required_for_writes": True,
            "allowed_tool_names": ["create_service_request"],
        },
    }

    response = client.post("/internal/agent/respond", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["response_type"] == "assistant_message_with_proposals"
    assert body["routing"]["primary_agent"] == "ServiceRequestAgent"
    assert body["proposals"][0]["tool_name"] == "create_service_request"


def test_respond_returns_booking_proposal_when_dates_are_present(client):
    payload = {
        "request_id": "req_2",
        "trace_id": "trace_2",
        "actor": {"actor_type": "guest", "user_id": "user_2"},
        "conversation": {
            "conversation_id": "conv_2",
            "channel": "mobile_chat",
            "language": "en",
        },
        "booking_context": {"resort_id": "resort_1"},
        "message": {
            "message_id": "msg_2",
            "content": "Please book a room for 2 adults and 0 children from 2026-05-01 to 2026-05-03.",
        },
        "policy_context": {
            "proposal_required_for_writes": True,
            "allowed_tool_names": ["create_booking"],
        },
    }

    response = client.post("/internal/agent/respond", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert body["proposals"][0]["tool_name"] == "create_booking"
    assert body["proposals"][0]["arguments"]["resort_id"] == "resort_1"
    assert body["proposals"][0]["arguments"]["adults"] == 2


def test_respond_lists_services_from_catalog(client):
    payload = {
        "request_id": "req_3",
        "trace_id": "trace_3",
        "actor": {"actor_type": "guest", "user_id": "user_3"},
        "conversation": {
            "conversation_id": "conv_3",
            "channel": "mobile_chat",
            "language": "en",
        },
        "booking_context": {"resort_id": "resort_1"},
        "message": {"message_id": "msg_3", "content": "What services do you have?"},
        "policy_context": {
            "proposal_required_for_writes": True,
            "allowed_tool_names": [],
        },
    }

    response = client.post("/internal/agent/respond", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["intent"]["primary"] == "service_catalog"
    assert "Sunset Spa Session" in body["assistant_message"]["content"]


def test_respond_creates_service_booking_proposal_for_selected_service(client):
    payload = {
        "request_id": "req_4",
        "trace_id": "trace_4",
        "actor": {"actor_type": "guest", "user_id": "user_4"},
        "conversation": {
            "conversation_id": "conv_4",
            "channel": "mobile_chat",
            "language": "en",
        },
        "booking_context": {"booking_id": "booking_123", "resort_id": "resort_1"},
        "message": {
            "message_id": "msg_4",
            "content": "Please add Sunset Spa Session to my booking.",
        },
        "policy_context": {
            "proposal_required_for_writes": True,
            "allowed_tool_names": ["create_service_booking"],
        },
    }

    response = client.post("/internal/agent/respond", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["routing"]["primary_agent"] == "RecommendationAgent"
    assert body["response_type"] == "clarification_required"
    assert "what date would you like" in body["assistant_message"]["content"].lower()
