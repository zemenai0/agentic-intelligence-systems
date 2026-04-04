"""Tests for backend route mapping and normalization."""

from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

from agentic_intelligence_systems.clients.backend_api import BackendAPIClient
from agentic_intelligence_systems.config import Settings
from agentic_intelligence_systems.contracts.common import ActorContext, ActorType


def build_actor() -> ActorContext:
    """Return a standard guest actor for backend client tests."""

    return ActorContext(actor_type=ActorType.GUEST, user_id="user_1")


@pytest.mark.asyncio
async def test_backend_client_builds_current_stay_context_from_domain_routes():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer backend-token"

        if request.url.path == "/api/admin/bookings/booking_123":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "booking_123",
                        "status": "confirmed",
                        "userId": "user_1",
                        "room": {
                            "id": "room_101",
                            "roomNumber": "101",
                            "type": "deluxe",
                            "status": "available",
                        },
                        "checkInDate": "2026-05-01",
                        "checkOutDate": "2026-05-03",
                    }
                },
            )

        if request.url.path == "/api/admin/services/requests":
            query = parse_qs(request.url.query.decode("utf-8"))
            assert query["bookingId"] == ["booking_123"]
            return httpx.Response(
                200,
                json={"data": [{"id": "sr_1", "type": "housekeeping", "status": "open"}]},
            )

        raise AssertionError(f"Unexpected route: {request.url.path}")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://backend.example",
    )
    backend = BackendAPIClient(
        Settings(
            backend_base_url="https://backend.example",
            backend_auth_mode="bearer",
            backend_service_token="backend-token",
        ),
        http_client=client,
    )

    stay_context = await backend.get_current_stay_context(
        request_id="req_1",
        trace_id="trace_1",
        actor=build_actor(),
        booking_id="booking_123",
    )

    assert stay_context.booking_id == "booking_123"
    assert stay_context.room and stay_context.room.room_number == "101"
    assert stay_context.open_service_requests[0].id == "sr_1"
    await client.aclose()


@pytest.mark.asyncio
async def test_backend_client_maps_room_inventory_and_service_catalog():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/rooms":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "room_101",
                            "type": "deluxe",
                            "status": "booked",
                            "basePriceCents": 18000,
                        }
                    ]
                },
            )

        if request.url.path == "/api/rooms/room_101/availability":
            return httpx.Response(200, json={"data": {"available": True}})

        if request.url.path == "/api/services/categories":
            return httpx.Response(
                200,
                json={"data": [{"id": "cat_1", "slug": "spa", "name": "Spa"}]},
            )

        if request.url.path == "/api/services":
            query = parse_qs(request.url.query.decode("utf-8"))
            assert query["categoryId"] == ["cat_1"]
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "svc_1",
                            "name": "Sunset Spa Session",
                            "categoryId": "cat_1",
                            "priceCents": 3500,
                            "available": True,
                        }
                    ]
                },
            )

        raise AssertionError(f"Unexpected route: {request.url.path}")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://backend.example",
    )
    backend = BackendAPIClient(
        Settings(backend_base_url="https://backend.example"),
        http_client=client,
    )

    rooms = await backend.search_room_inventory(
        request_id="req_2",
        trace_id="trace_2",
        actor=build_actor(),
        arguments={
            "resort_id": "resort_1",
            "check_in_date": "2026-05-01",
            "check_out_date": "2026-05-03",
        },
    )
    services = await backend.get_service_catalog(
        request_id="req_3",
        trace_id="trace_3",
        actor=build_actor(),
        category_slug="spa",
    )

    assert rooms[0].id == "room_101"
    assert rooms[0].availability is True
    assert services[0].name == "Sunset Spa Session"
    assert services[0].category == "spa"
    await client.aclose()
