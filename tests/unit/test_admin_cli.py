"""Tests for the admin inventory CLI helpers."""

from __future__ import annotations

import httpx
import pytest

from agentic_intelligence_systems.cli.admin import load_existing_room_numbers
from agentic_intelligence_systems.cli.inventory_seed import build_demo_room_payloads


def test_build_demo_room_payloads_returns_realistic_inventory():
    payloads = build_demo_room_payloads("resort_1")

    assert [payload["roomNumber"] for payload in payloads] == ["201", "202", "301"]
    assert payloads[0]["type"] == "deluxe"
    assert payloads[-1]["accessible"] is True


@pytest.mark.asyncio
async def test_load_existing_room_numbers_reads_admin_room_list():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/admin/rooms"
        return httpx.Response(
            200,
            json={"data": [{"roomNumber": "100"}, {"roomNumber": "201"}]},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://backend.example",
    ) as client:
        room_numbers = await load_existing_room_numbers(
            client,
            {"cookie": "session=value"},
            "resort_1",
        )

    assert room_numbers == {"100", "201"}
