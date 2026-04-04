"""Async client for the current backend API surface."""

from __future__ import annotations

from typing import Any

import httpx

from agentic_intelligence_systems.clients import backend_normalizers as normalizers
from agentic_intelligence_systems.clients import backend_routes
from agentic_intelligence_systems.clients.backend_availability import (
    load_availability_overrides,
)
from agentic_intelligence_systems.config import Settings
from agentic_intelligence_systems.contracts.common import ActorContext
from agentic_intelligence_systems.contracts.tools import (
    BookingRecord,
    CheckInReadiness,
    CurrentStayContext,
    ResortCatalogItem,
    RoomInventoryItem,
    RoomStatusSnapshot,
    ServiceCatalogItem,
)


class BackendToolError(RuntimeError):
    """Raised when the backend route layer is unavailable or invalid."""


class BackendAPIClient:
    """Map logical tool reads onto the backend's current domain routes."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.backend_base_url,
            timeout=settings.backend_timeout_seconds,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""

        if self._owns_client:
            await self._client.aclose()

    async def get_current_stay_context(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        booking_id: str,
    ) -> CurrentStayContext:
        booking = await self.get_booking_record(
            request_id=request_id,
            trace_id=trace_id,
            actor=actor,
            booking_id=booking_id,
        )
        service_requests = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.booking_service_requests(booking_id),
        )
        return normalizers.normalize_current_stay_context(booking, service_requests)

    async def get_resort_catalog(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        search: str | None = None,
    ) -> list[ResortCatalogItem]:
        del actor
        payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.resort_catalog(search=search),
        )
        return normalizers.normalize_resort_catalog(payload)

    async def search_room_inventory(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        arguments: dict[str, Any],
    ) -> list[RoomInventoryItem]:
        del actor
        list_payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.room_list(
                {
                    "resortId": arguments.get("resort_id"),
                    "type": arguments.get("room_type"),
                    "floor": arguments.get("floor"),
                }
            ),
        )
        availability_by_room = await load_availability_overrides(
            request_json=self._request_json,
            request_id=request_id,
            trace_id=trace_id,
            rooms_payload=list_payload,
            check_in_date=arguments.get("check_in_date"),
            check_out_date=arguments.get("check_out_date"),
        )
        return normalizers.normalize_room_inventory(
            list_payload,
            availability_by_room=availability_by_room,
        )

    async def get_booking_record(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        booking_id: str,
    ) -> BookingRecord:
        del actor
        payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.booking_detail(booking_id),
        )
        return normalizers.normalize_booking_record(payload)

    async def get_check_in_readiness(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        booking_id: str,
    ) -> CheckInReadiness:
        booking = await self.get_booking_record(
            request_id=request_id,
            trace_id=trace_id,
            actor=actor,
            booking_id=booking_id,
        )
        room_snapshot = None
        if booking.room and booking.room.id:
            room_snapshot = await self.get_room_status_snapshot(
                request_id=request_id,
                trace_id=trace_id,
                actor=actor,
                room_id=booking.room.id,
            )
        return normalizers.derive_check_in_readiness(booking, room_snapshot)

    async def get_room_status_snapshot(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        room_id: str,
    ) -> RoomStatusSnapshot:
        del actor
        room_payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.room_detail(room_id),
        )
        log_payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.room_status_log(room_id),
        )
        return normalizers.normalize_room_status_snapshot(room_payload, log_payload)

    async def get_service_catalog(
        self,
        *,
        request_id: str,
        trace_id: str,
        actor: ActorContext,
        resort_id: str | None = None,
        category_slug: str | None = None,
    ) -> list[ServiceCatalogItem]:
        del actor, resort_id
        category_payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.service_categories(),
        )
        category_lookup = normalizers.build_category_lookup(category_payload)
        category_id = category_lookup.get(category_slug.lower()) if category_slug else None
        services_payload = await self._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.service_catalog(category_id),
        )
        return normalizers.normalize_service_catalog(
            services_payload,
            category_names=normalizers.invert_category_lookup(category_lookup),
        )

    async def _request_json(
        self,
        *,
        request_id: str,
        trace_id: str,
        route: backend_routes.BackendRouteSpec,
    ) -> Any:
        try:
            response = await self._client.request(
                route.method,
                route.path,
                params=route.params,
                json=route.json_body,
                headers=self._build_headers(request_id, trace_id),
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BackendToolError(f"Backend request failed for {route.path}.") from exc
        return response.json()

    def _build_headers(self, request_id: str, trace_id: str) -> dict[str, str]:
        headers = {
            "x-request-id": request_id,
            "x-trace-id": trace_id,
        }
        if self._settings.backend_auth_mode == "api_key" and self._settings.backend_api_key:
            headers["x-api-key"] = self._settings.backend_api_key
        if (
            self._settings.backend_auth_mode == "bearer"
            and self._settings.backend_service_token
        ):
            headers["authorization"] = f"Bearer {self._settings.backend_service_token}"
        if self._settings.backend_session_cookie:
            headers["cookie"] = self._settings.backend_session_cookie
        return headers
