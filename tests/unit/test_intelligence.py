"""Tests for recommendation, sentiment, and memory endpoints."""

from __future__ import annotations


def test_recommend_endpoint_returns_ranked_results(client):
    payload = {
        "request_id": "req_3",
        "trace_id": "trace_3",
        "actor": {"actor_type": "guest", "user_id": "user_1"},
        "booking_context": {"resort_id": "resort_1"},
        "recommendation_scope": {
            "category": "spa",
            "time_window": "tonight",
            "max_results": 2,
        },
    }

    response = client.post("/internal/agent/recommend", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]
    assert body["recommendations"][0]["category"] == "spa"


def test_sentiment_endpoint_flags_high_risk_messages(client):
    payload = {
        "request_id": "req_4",
        "trace_id": "trace_4",
        "conversation_id": "conv_4",
        "message": {
            "message_id": "msg_4",
            "role": "user",
            "content": "This is terrible and nobody is helping. The room is too hot.",
        },
    }

    response = client.post("/internal/agent/sentiment/score", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["sentiment"]["label"] == "negative"
    assert body["risk"]["handover_required"] is True


def test_memory_summarize_extracts_preference_signals(client):
    payload = {
        "request_id": "req_5",
        "trace_id": "trace_5",
        "conversation_id": "conv_5",
        "booking_id": "booking_123",
        "user_id": "user_1",
        "message_ids": ["msg_1", "msg_2"],
        "messages": [
            {
                "message_id": "msg_1",
                "role": "user",
                "content": "I prefer quiet dinner spots.",
            },
            {
                "message_id": "msg_2",
                "role": "user",
                "content": "Please schedule housekeeping later in the day.",
            },
        ],
    }

    response = client.post("/internal/agent/memory/summarize", json=payload)

    assert response.status_code == 200
    body = response.json()
    keys = {signal["key"] for signal in body["candidate_signals"]}
    assert "quiet_dining" in keys
    assert "late_housekeeping" in keys
