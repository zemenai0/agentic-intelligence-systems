"""Tests for CLI execution helpers."""

from __future__ import annotations

import asyncio

from agentic_intelligence_systems.cli.chat import (
    _build_booking_success_message,
    _build_service_summary_message,
    should_auto_execute_confirmation,
)
from agentic_intelligence_systems.clients.proposal_execution import (
    ProposalExecutionResult,
    execute_proposal,
)
from agentic_intelligence_systems.contracts.common import Proposal, RiskLevel
from agentic_intelligence_systems.contracts.tools import BookingRecord, RoomSummary


def test_auto_executes_only_explicit_room_confirmation():
    proposal = Proposal(
        tool_name="create_booking",
        action_summary="Book room",
        risk_level=RiskLevel.MEDIUM_TRANSACTIONAL,
        arguments={},
        idempotency_key="abc",
    )
    assert should_auto_execute_confirmation("please book the room", [proposal]) is True
    assert should_auto_execute_confirmation("book now", [proposal]) is True
    assert should_auto_execute_confirmation("I want to book a room next month", [proposal]) is False


def test_booking_success_message_is_guest_facing():
    execution = ProposalExecutionResult(
        tool_name="create_booking",
        raw_result={},
        booking=BookingRecord(
            booking_id="booking_123",
            resort_id="resort_1",
            status="pending",
            room=RoomSummary(
                id="room_104",
                room_number="104",
                room_type="Suite",
                status="available",
            ),
            check_in_date="2026-09-03",
            check_out_date="2026-09-05",
            adults=2,
            children=0,
            total_price_cents=120000,
        ),
        service_name="Deep Tissue Massage",
    )

    assert (
        _build_booking_success_message(execution)
        == "You have booked room 104 - suite for USD 1200.00. Your booking ID is booking_123."
    )
    assert _build_service_summary_message(execution) == (
        "Additional requested service: Deep Tissue Massage."
    )


def test_service_summary_uses_booked_wording_when_service_booking_exists():
    execution = ProposalExecutionResult(
        tool_name="create_booking",
        raw_result={},
        booking=BookingRecord(
            booking_id="booking_123",
            resort_id="resort_1",
            total_price_cents=120000,
        ),
        service_name="Deep Tissue Massage",
        service_booking_total_cents=3500,
    )

    assert _build_service_summary_message(execution) == (
        "Additional service booked: Deep Tissue Massage for USD 35.00."
    )


def test_execute_booking_proposal_maps_to_backend_route():
    captured = {"routes": []}

    class FakeBackend:
        async def _request_json(self, *, request_id, trace_id, route):
            captured["request_id"] = request_id
            captured["trace_id"] = trace_id
            captured["routes"].append(route)
            if route.path == "/api/bookings":
                return {
                    "data": {
                        "id": "booking_999",
                        "resortId": "resort_1",
                        "roomId": "room_201",
                        "roomNumber": "201",
                        "type": "Deluxe",
                        "status": "confirmed",
                        "checkInDate": "2026-07-05",
                        "checkOutDate": "2026-07-07",
                        "totalPriceCents": 64000,
                    }
                }
            return {
                "data": {
                    "id": "service_booking_1",
                    "totalPriceCents": 3500,
                }
            }

    proposal = Proposal(
        tool_name="create_booking",
        action_summary="Book room 201",
        risk_level=RiskLevel.MEDIUM_TRANSACTIONAL,
        arguments={
            "room_id": "room_201",
            "resort_id": "resort_1",
            "check_in_date": "2026-07-05",
            "check_out_date": "2026-07-07",
            "adults": 2,
            "children": 0,
            "special_requests": "Selected add-on service: Deep Tissue Massage",
            "pending_service_id": "svc_spa",
            "pending_service_name": "Deep Tissue Massage",
            "pending_service_scheduled_at": "2026-07-05T10:00:00.000Z",
        },
        idempotency_key="booking_key",
    )

    result = asyncio.run(
        execute_proposal(
            FakeBackend(),
            request_id="req_exec",
            trace_id="trace_exec",
            proposal=proposal,
        )
    )

    assert captured["routes"][0].path == "/api/bookings"
    assert captured["routes"][0].json_body["roomId"] == "room_201"
    assert captured["routes"][1].path == "/api/bookings/me/booking_999/services"
    assert captured["routes"][1].json_body["serviceId"] == "svc_spa"
    assert result.booking is not None
    assert result.booking.booking_id == "booking_999"
    assert result.booking.total_price_cents == 64000
    assert result.service_booking_total_cents == 3500
    assert result.service_name == "Deep Tissue Massage"


def test_execute_booking_proposal_defers_service_until_booking_confirmed():
    captured = {"routes": []}

    class FakeBackend:
        async def _request_json(self, *, request_id, trace_id, route):
            captured["routes"].append(route)
            return {
                "data": {
                    "id": "booking_pending_1",
                    "resortId": "resort_1",
                    "roomId": "room_100",
                    "roomNumber": "100",
                    "type": "Standard",
                    "status": "pending",
                    "checkInDate": "2026-07-05",
                    "checkOutDate": "2026-07-07",
                    "totalPriceCents": 50000,
                }
            }

    proposal = Proposal(
        tool_name="create_booking",
        action_summary="Book room 100",
        risk_level=RiskLevel.MEDIUM_TRANSACTIONAL,
        arguments={
            "room_id": "room_100",
            "resort_id": "resort_1",
            "check_in_date": "2026-07-05",
            "check_out_date": "2026-07-07",
            "adults": 2,
            "children": 0,
            "special_requests": "Selected add-on service: Deep Tissue Massage",
            "pending_service_id": "svc_spa",
            "pending_service_name": "Deep Tissue Massage",
            "pending_service_scheduled_at": "2026-07-05T10:00:00.000Z",
        },
        idempotency_key="booking_key_pending",
    )

    result = asyncio.run(
        execute_proposal(
            FakeBackend(),
            request_id="req_exec",
            trace_id="trace_exec",
            proposal=proposal,
        )
    )

    assert len(captured["routes"]) == 1
    assert captured["routes"][0].path == "/api/bookings"
    assert result.booking is not None
    assert result.booking.booking_id == "booking_pending_1"
    assert result.booking.status == "pending"
    assert result.service_booking_total_cents is None
    assert result.service_message is not None
    assert "has not been booked yet" in result.service_message
    assert "saved it in the reservation request" in result.service_message
