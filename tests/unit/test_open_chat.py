"""Tests for open-domain conversational behavior."""

from __future__ import annotations


def test_responds_to_greeting_without_task_gate(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_greet",
            "trace_id": "trace_greet",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_1",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {},
            "message": {"message_id": "msg_greet", "content": "hey"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert body["intent"]["primary"] == "welcome"
    assert body["routing"]["primary_agent"] == "WelcomeAgent"
    assert "branches" in body["assistant_message"]["content"].lower()


def test_uses_full_message_when_greeting_contains_booking_intent(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_greet_booking",
            "trace_id": "trace_greet_booking",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_1b",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_greet_booking",
                "content": "hello i want to book a room for tomorrow",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert "how long will you stay" in body["assistant_message"]["content"].lower()


def test_routes_semantic_branch_request_without_exact_old_phrase(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_semantic",
            "trace_id": "trace_branch_semantic",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_branch_semantic",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_semantic",
                "content": "can you show me your resorts right now",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "branch_catalog"
    assert body["routing"]["primary_agent"] == "WelcomeAgent"


def test_routes_semantic_stay_request_into_booking_flow(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_semantic_stay",
            "trace_id": "trace_semantic_stay",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_stay_semantic",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_semantic_stay",
                "content": "I need a room to stay tomorrow for 2 days",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert "how many adults and children" in body["assistant_message"]["content"].lower()


def test_responds_to_identity_question(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_identity",
            "trace_id": "trace_identity",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_2",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_identity", "content": "who are you"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert body["intent"]["primary"] == "identity"
    assert "habitalife" in body["assistant_message"]["content"].lower()


def test_answers_general_knowledge_question(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_knowledge",
            "trace_id": "trace_knowledge",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_3",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_knowledge",
                "content": "when america founded",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert body["intent"]["primary"] == "general_knowledge"
    assert body["routing"]["primary_agent"] == "SearchKnowledgeAgent"
    assert "1776" in body["assistant_message"]["content"]


def test_routes_explain_style_knowledge_question(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_inflation",
            "trace_id": "trace_inflation",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_3b",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_inflation",
                "content": "explain what inflation is",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert body["intent"]["primary"] == "general_knowledge"
    assert "rise in prices" in body["assistant_message"]["content"].lower()


def test_reframes_hostile_turn_without_loop(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_hostile",
            "trace_id": "trace_hostile",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_4",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_hostile", "content": "fuck you"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert body["intent"]["primary"] == "hostile_repair"
    assert "help" in body["assistant_message"]["content"].lower()


def test_general_support_does_not_repeat_old_gate(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_general",
            "trace_id": "trace_general",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_5",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_general", "content": "please tell me"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["response_type"] == "assistant_message"
    assert body["intent"]["primary"] == "general_support"
    assert "happy to help" in body["assistant_message"]["content"].lower()


def test_greeting_with_travel_context_uses_full_message(client):
    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_travel_greeting",
            "trace_id": "trace_travel_greeting",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": {
                "conversation_id": "conv_open_5b",
                "channel": "mobile_chat",
                "language": "en",
            },
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_travel_greeting",
                "content": "hello i am excited to visit africa",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": [],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "greeting"
    assert "sounds exciting" in body["assistant_message"]["content"].lower()


def test_greeting_interrupts_booking_state_without_losing_context(client):
    conversation = {
        "conversation_id": "conv_open_6",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_booking_start",
            "trace_id": "trace_booking_start",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_booking_start",
                "content": "I want a booking for 2 adults and 0 children from 2026-07-05 to 2026-07-07.",
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
            "request_id": "req_booking_interrupt",
            "trace_id": "trace_booking_interrupt",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_booking_interrupt", "content": "hello"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert "nearby availability" in body["assistant_message"]["content"].lower()


def test_hostile_turn_soft_resets_booking_context(client):
    conversation = {
        "conversation_id": "conv_open_7",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_booking_reset_1",
            "trace_id": "trace_booking_reset_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_booking_reset_1",
                "content": "I want a booking for 2 adults and 0 children from 2026-07-05 to 2026-07-07",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    hostile = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_booking_reset_2",
            "trace_id": "trace_booking_reset_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_booking_reset_2", "content": "fuck you"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    hostile_body = hostile.json()
    assert "start fresh" in hostile_body["assistant_message"]["content"].lower()

    greeting = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_booking_reset_3",
            "trace_id": "trace_booking_reset_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {"message_id": "msg_booking_reset_3", "content": "hello"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    greeting_body = greeting.json()
    assert "working on" not in greeting_body["assistant_message"]["content"].lower()


def test_knowledge_fallback_stays_in_character_and_drops_old_task_context(client):
    conversation = {
        "conversation_id": "conv_open_8",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_knowledge_reset_1",
            "trace_id": "trace_knowledge_reset_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_knowledge_reset_1",
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
            "request_id": "req_knowledge_reset_2",
            "trace_id": "trace_knowledge_reset_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {"resort_id": "resort_1"},
            "message": {
                "message_id": "msg_knowledge_reset_2",
                "content": "tell me about usa iran war",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "general_knowledge"
    assert "provider" not in body["assistant_message"]["content"].lower()
    assert "room search" not in body["assistant_message"]["content"].lower()


def test_branch_question_and_selection_stay_in_reservation_flow(client):
    conversation = {
        "conversation_id": "conv_open_branch_1",
        "channel": "mobile_chat",
        "language": "en",
    }

    branches = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_1",
            "trace_id": "trace_branch_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_1",
                "content": "what are the branchs currently are",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    branch_body = branches.json()
    assert branch_body["routing"]["primary_agent"] == "WelcomeAgent"
    assert "branch" in branch_body["assistant_message"]["content"].lower()

    selection = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_2",
            "trace_id": "trace_branch_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_2",
                "content": "HabitaLife Water Park Bishoftu",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    selection_body = selection.json()
    assert selection_body["intent"]["primary"] == "booking_search"
    assert "check-in and check-out dates" in selection_body["assistant_message"]["content"].lower()

    reservation = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_3",
            "trace_id": "trace_branch_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_3",
                "content": "I want to reserve a room",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    reservation_body = reservation.json()
    assert reservation_body["intent"]["primary"] == "booking_search"
    assert "booking id" not in reservation_body["assistant_message"]["content"].lower()


def test_branch_follow_up_keeps_branch_selection_state(client):
    conversation = {
        "conversation_id": "conv_open_branch_2",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_follow_1",
            "trace_id": "trace_branch_follow_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {"message_id": "msg_branch_follow_1", "content": "hello"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_follow_2",
            "trace_id": "trace_branch_follow_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_follow_2",
                "content": "what branches do you currently have?",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["routing"]["primary_agent"] == "WelcomeAgent"
    assert "branch" in body["assistant_message"]["content"].lower()

    selection = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_follow_3",
            "trace_id": "trace_branch_follow_3",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_follow_3",
                "content": "HabitaLife Water Park Bishoftu",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    selection_body = selection.json()
    assert selection_body["intent"]["primary"] == "booking_search"
    assert "check-in and check-out dates" in selection_body["assistant_message"]["content"].lower()


def test_branch_selection_accepts_fuzzy_branch_text(client):
    conversation = {
        "conversation_id": "conv_open_branch_3",
        "channel": "mobile_chat",
        "language": "en",
    }

    client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_fuzzy_1",
            "trace_id": "trace_branch_fuzzy_1",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {"message_id": "msg_branch_fuzzy_1", "content": "hello"},
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )

    response = client.post(
        "/internal/agent/respond",
        json={
            "request_id": "req_branch_fuzzy_2",
            "trace_id": "trace_branch_fuzzy_2",
            "actor": {"actor_type": "guest", "user_id": "user_1"},
            "conversation": conversation,
            "booking_context": {},
            "message": {
                "message_id": "msg_branch_fuzzy_2",
                "content": "HabitaLife Water Pirk Bishoftu",
            },
            "policy_context": {
                "proposal_required_for_writes": True,
                "allowed_tool_names": ["create_booking"],
            },
        },
    )
    body = response.json()
    assert body["intent"]["primary"] == "booking_search"
    assert "check-in and check-out dates" in body["assistant_message"]["content"].lower()
