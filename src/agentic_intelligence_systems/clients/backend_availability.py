"""Availability helpers for backend room inventory lookups."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from agentic_intelligence_systems.clients import backend_normalizers as normalizers
from agentic_intelligence_systems.clients import backend_routes


RequestJson = Callable[..., Awaitable[Any]]


async def load_availability_overrides(
    *,
    request_json: RequestJson,
    request_id: str,
    trace_id: str,
    rooms_payload: Any,
    check_in_date: str | None,
    check_out_date: str | None,
) -> dict[str, bool]:
    """Return room-level availability overrides for the supplied stay dates."""

    if not check_in_date or not check_out_date:
        return {}

    room_items = normalizers.extract_collection(rooms_payload)[:8]
    tasks = [
        request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.room_availability(
                str(room.get("id")),
                check_in_date=check_in_date,
                check_out_date=check_out_date,
            ),
        )
        for room in room_items
        if room.get("id")
    ]
    payloads = await asyncio.gather(*tasks, return_exceptions=True)

    availability: dict[str, bool] = {}
    for room, payload in zip(room_items, payloads, strict=False):
        room_id = str(room.get("id"))
        if isinstance(payload, Exception):
            availability[room_id] = False
            continue
        availability[room_id] = normalizers.parse_room_availability(payload)
    return availability
