"""Normalize backend responses into stable agent-side models."""

from __future__ import annotations

from typing import Any

from agentic_intelligence_systems.contracts.tools import (
    BookingRecord,
    CheckInReadiness,
    CurrentStayContext,
    OpenServiceRequestSummary,
    ResortCatalogItem,
    RoomInventoryItem,
    RoomStatusSnapshot,
    RoomSummary,
    ServiceCatalogItem,
)


def unwrap_payload(payload: Any) -> Any:
    """Return the most useful response body segment."""
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def extract_collection(payload: Any) -> list[dict[str, Any]]:
    """Extract a list payload from common collection wrappers."""
    data = unwrap_payload(payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "results", "rows", "services", "requests", "rooms"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def pick_value(source: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value from the given keys."""
    for key in keys:
        if key in source and source[key] is not None:
            return source[key]
    return None


def normalize_room_summary(payload: dict[str, Any]) -> RoomSummary:
    """Normalize a room-like payload."""
    return RoomSummary(
        id=str(pick_value(payload, "id", "roomId", "room_id")),
        room_number=pick_value(payload, "roomNumber", "room_number"),
        room_type=pick_value(payload, "type", "roomType", "room_type"),
        status=pick_value(payload, "status"),
    )


def normalize_booking_record(payload: Any) -> BookingRecord:
    """Normalize booking detail payloads."""

    data = unwrap_payload(payload)
    room_payload = data.get("room") if isinstance(data, dict) else None
    if not room_payload and isinstance(data, dict) and pick_value(data, "roomId", "room_id"):
        room_payload = {
            "id": pick_value(data, "roomId", "room_id"),
            "roomNumber": pick_value(data, "roomNumber", "room_number"),
            "type": pick_value(data, "type", "roomType", "room_type"),
            "status": pick_value(data, "roomStatus", "room_status"),
        }
    return BookingRecord(
        booking_id=str(pick_value(data, "id", "bookingId", "booking_id")),
        resort_id=pick_value(data, "resortId", "resort_id"),
        status=pick_value(data, "status"),
        guest_user_id=pick_value(data, "userId", "user_id", "guestUserId", "guest_user_id"),
        room=normalize_room_summary(room_payload) if isinstance(room_payload, dict) else None,
        check_in_date=pick_value(data, "checkInDate", "check_in_date"),
        check_out_date=pick_value(data, "checkOutDate", "check_out_date"),
        adults=pick_value(data, "adults"),
        children=pick_value(data, "children"),
        total_price_cents=pick_value(data, "totalPriceCents", "total_price_cents"),
        special_requests=pick_value(data, "specialRequests", "special_requests"),
    )


def normalize_current_stay_context(
    booking: BookingRecord,
    service_requests_payload: Any,
) -> CurrentStayContext:
    """Combine booking detail and service requests into stay context."""

    service_requests = [
        OpenServiceRequestSummary(
            id=str(pick_value(item, "id", "serviceRequestId", "service_request_id")),
            type=str(pick_value(item, "type", "category", "requestType") or "general"),
            status=str(pick_value(item, "status") or "open"),
        )
        for item in extract_collection(service_requests_payload)
    ]
    return CurrentStayContext(
        booking_id=booking.booking_id,
        guest_user_id=booking.guest_user_id,
        room=booking.room,
        stay_status=booking.status,
        open_service_requests=service_requests,
    )


def normalize_room_inventory(
    payload: Any,
    *,
    availability_by_room: dict[str, bool] | None = None,
) -> list[RoomInventoryItem]:
    """Normalize room list payloads into inventory items."""

    availability_by_room = availability_by_room or {}
    items: list[RoomInventoryItem] = []
    for room in extract_collection(payload):
        room_id = str(pick_value(room, "id", "roomId", "room_id"))
        items.append(
            RoomInventoryItem(
                id=room_id,
                room_type=str(pick_value(room, "type", "roomType", "room_type") or "unknown"),
                room_number=pick_value(room, "roomNumber", "room_number"),
                rate_amount=pick_value(room, "basePriceCents", "base_price_cents", "priceCents"),
                currency=pick_value(room, "currency") or "USD",
                floor=pick_value(room, "floor"),
                size_sqm=pick_value(room, "sizeSqm", "size_sqm"),
                max_guests=pick_value(room, "maxGuests", "max_guests"),
                bed_configuration=pick_value(
                    room,
                    "bedConfiguration",
                    "bed_configuration",
                ),
                accessible=bool(pick_value(room, "accessible") or False),
                notes=pick_value(room, "notes"),
                amenities=[
                    str(item)
                    for item in pick_value(room, "amenities") or []
                    if isinstance(item, str)
                ],
                availability=availability_by_room.get(
                    room_id,
                    str(pick_value(room, "status") or "").lower() == "available",
                ),
            )
        )
    return items


def normalize_resort_catalog(payload: Any) -> list[ResortCatalogItem]:
    """Normalize resort list payloads."""

    resorts: list[ResortCatalogItem] = []
    for item in extract_collection(payload):
        resorts.append(
            ResortCatalogItem(
                id=str(pick_value(item, "id", "resortId", "resort_id")),
                name=str(pick_value(item, "name") or "Unnamed Resort"),
                location=pick_value(item, "location"),
                currency=pick_value(item, "currency"),
                check_in_time=pick_value(item, "checkInTime", "check_in_time"),
                check_out_time=pick_value(item, "checkOutTime", "check_out_time"),
                max_nights=pick_value(item, "maxNights", "max_nights"),
            )
        )
    return resorts


def normalize_room_status_snapshot(
    room_payload: Any,
    status_log_payload: Any,
) -> RoomStatusSnapshot:
    """Combine room detail and status logs into a room status snapshot."""

    room_data = unwrap_payload(room_payload)
    logs = extract_collection(status_log_payload)
    previous_summary = None
    if logs:
        latest = logs[0]
        previous_summary = pick_value(latest, "reason", "summary", "note")
    return RoomStatusSnapshot(
        room_id=str(pick_value(room_data, "id", "roomId", "room_id")),
        state=str(pick_value(room_data, "status") or "unknown"),
        maintenance_lock=str(pick_value(room_data, "status") or "").lower() == "in_maintenance",
        previous_transition_summary=previous_summary,
    )


def build_category_lookup(payload: Any) -> dict[str, str]:
    """Map category slug and name to category IDs."""

    lookup: dict[str, str] = {}
    for item in extract_collection(payload):
        category_id = str(pick_value(item, "id", "categoryId", "category_id"))
        slug = pick_value(item, "slug")
        name = pick_value(item, "name")
        if category_id and slug:
            lookup[slug.lower()] = category_id
        if category_id and name:
            lookup[name.lower()] = category_id
    return lookup


def invert_category_lookup(category_lookup: dict[str, str]) -> dict[str, str]:
    """Map category IDs back to readable names or slugs."""

    category_names: dict[str, str] = {}
    for key, value in category_lookup.items():
        category_names.setdefault(value, key)
    return category_names


def normalize_service_catalog(
    payload: Any,
    *,
    category_names: dict[str, str] | None = None,
) -> list[ServiceCatalogItem]:
    """Normalize service catalog payloads."""

    category_names = category_names or {}
    services: list[ServiceCatalogItem] = []
    for item in extract_collection(payload):
        category_id = str(pick_value(item, "categoryId", "category_id") or "")
        category = (
            pick_value(item, "category", "categoryName", "category_name")
            or category_names.get(category_id)
            or category_id
            or "general"
        )
        services.append(
            ServiceCatalogItem(
                id=str(pick_value(item, "id", "serviceId", "service_id")),
                name=str(pick_value(item, "name") or "Unnamed Service"),
                category=str(category),
                price=pick_value(item, "priceCents", "price_cents"),
                currency=pick_value(item, "currency") or "USD",
                availability="available" if pick_value(item, "available") is not False else "unavailable",
                description=pick_value(item, "description"),
                duration_mins=pick_value(item, "durationMins", "duration_mins"),
            )
        )
    return services


def parse_room_availability(payload: Any) -> bool:
    """Extract a boolean availability flag."""

    data = unwrap_payload(payload)
    if isinstance(data, bool):
        return data
    if isinstance(data, dict):
        value = pick_value(data, "available", "isAvailable", "availability")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"true", "available", "yes"}
        status = pick_value(data, "status")
        if isinstance(status, str):
            return status.lower() == "available"
    return False


def derive_check_in_readiness(
    booking: BookingRecord,
    room_snapshot: RoomStatusSnapshot | None,
) -> CheckInReadiness:
    """Derive check-in readiness from booking and room state."""

    status = (booking.status or "").lower()
    room_state = (room_snapshot.state if room_snapshot else "").lower()
    if status == "checked_in":
        return CheckInReadiness(
            booking_id=booking.booking_id,
            status="already_checked_in",
            reason="Booking is already checked in.",
        )
    if status in {"cancelled", "canceled", "no_show"}:
        return CheckInReadiness(
            booking_id=booking.booking_id,
            status="not_eligible",
            reason="Booking is not eligible for check-in in its current state.",
        )
    if room_state in {"in_maintenance", "cleaning"}:
        return CheckInReadiness(
            booking_id=booking.booking_id,
            status="not_ready",
            reason="The assigned room is not ready yet.",
        )
    return CheckInReadiness(
        booking_id=booking.booking_id,
        status="eligible",
        reason="Booking is confirmed and room readiness does not show a blocker.",
    )
