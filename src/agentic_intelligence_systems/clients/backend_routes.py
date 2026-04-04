"""Route mapping for the current backend API surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BackendRouteSpec:
    """Simple request spec used by the backend API client."""

    method: str
    path: str
    params: dict[str, Any] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None


def booking_detail(booking_id: str) -> BackendRouteSpec:
    return BackendRouteSpec("GET", f"/api/admin/bookings/{booking_id}")


def booking_service_requests(
    booking_id: str,
    status: str = "open",
) -> BackendRouteSpec:
    return BackendRouteSpec(
        "GET",
        "/api/admin/services/requests",
        params={"bookingId": booking_id, "status": status},
    )


def resort_catalog(search: str | None = None) -> BackendRouteSpec:
    params: dict[str, Any] = {"page": 1, "limit": 20}
    if search:
        params["search"] = search
    return BackendRouteSpec("GET", "/api/admin/resorts", params=params)


def room_list(filters: dict[str, Any]) -> BackendRouteSpec:
    params = {"page": 1, "limit": 20}
    params.update({key: value for key, value in filters.items() if value is not None})
    return BackendRouteSpec("GET", "/api/admin/rooms", params=params)


def room_availability(
    room_id: str,
    *,
    check_in_date: str,
    check_out_date: str,
) -> BackendRouteSpec:
    return BackendRouteSpec(
        "GET",
        f"/api/rooms/{room_id}/availability",
        params={
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
        },
    )


def room_detail(room_id: str) -> BackendRouteSpec:
    return BackendRouteSpec("GET", f"/api/rooms/{room_id}")


def room_status_log(room_id: str) -> BackendRouteSpec:
    return BackendRouteSpec("GET", f"/api/rooms/{room_id}/status-log")


def service_categories() -> BackendRouteSpec:
    return BackendRouteSpec("GET", "/api/services/categories")


def service_catalog(category_id: str | None = None) -> BackendRouteSpec:
    params: dict[str, Any] = {"available": "true"}
    if category_id:
        params["categoryId"] = category_id
    return BackendRouteSpec("GET", "/api/services", params=params)


def create_booking(body: dict[str, Any]) -> BackendRouteSpec:
    return BackendRouteSpec("POST", "/api/bookings", json_body=body)


def create_service_request(
    booking_id: str,
    body: dict[str, Any],
) -> BackendRouteSpec:
    return BackendRouteSpec(
        "POST",
        f"/api/bookings/me/{booking_id}/service-requests",
        json_body=body,
    )


def create_service_booking(
    booking_id: str,
    body: dict[str, Any],
) -> BackendRouteSpec:
    return BackendRouteSpec(
        "POST",
        f"/api/bookings/me/{booking_id}/services",
        json_body=body,
    )


def admin_check_in(booking_id: str) -> BackendRouteSpec:
    return BackendRouteSpec("POST", f"/api/admin/bookings/{booking_id}/check-in")


def admin_check_out(booking_id: str) -> BackendRouteSpec:
    return BackendRouteSpec("POST", f"/api/admin/bookings/{booking_id}/check-out")
