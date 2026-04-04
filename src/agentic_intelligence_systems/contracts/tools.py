"""Internal tool envelopes and result models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from agentic_intelligence_systems.contracts.common import (
    ActorContext,
    ContractModel,
    ToolType,
)


class ToolExecutionRequest(ContractModel):
    request_id: str
    tool_name: str
    tool_type: ToolType
    actor: ActorContext
    reason: str
    arguments: dict[str, Any]


class ToolAudit(ContractModel):
    tool_name: str
    executed_at: str


class ToolError(ContractModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ToolExecutionResponse(ContractModel):
    request_id: str
    tool_name: str
    ok: bool
    result: dict[str, Any] | list[dict[str, Any]] | None = None
    error: ToolError | None = None
    audit: ToolAudit | None = None


class ResortCatalogItem(ContractModel):
    id: str
    name: str
    location: str | None = None
    currency: str | None = None
    check_in_time: str | None = None
    check_out_time: str | None = None
    max_nights: int | None = None


class RoomSummary(ContractModel):
    id: str
    room_number: str | None = None
    room_type: str | None = None
    status: str | None = None


class OpenServiceRequestSummary(ContractModel):
    id: str
    type: str
    status: str


class CurrentStayContext(ContractModel):
    booking_id: str
    guest_user_id: str | None = None
    room: RoomSummary | None = None
    stay_status: str | None = None
    open_service_requests: list[OpenServiceRequestSummary] = Field(default_factory=list)


class BookingRecord(ContractModel):
    booking_id: str
    resort_id: str | None = None
    status: str | None = None
    guest_user_id: str | None = None
    room: RoomSummary | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    adults: int | None = None
    children: int | None = None
    total_price_cents: int | None = None
    special_requests: str | None = None


class CheckInReadiness(ContractModel):
    booking_id: str
    status: str
    reason: str


class RoomStatusSnapshot(ContractModel):
    room_id: str
    state: str
    maintenance_lock: bool = False
    previous_transition_summary: str | None = None


class ServiceCatalogItem(ContractModel):
    id: str
    name: str
    category: str
    price: float | None = None
    currency: str | None = None
    availability: str | None = None
    description: str | None = None
    duration_mins: int | None = None


class RoomInventoryItem(ContractModel):
    id: str
    room_type: str
    room_number: str | None = None
    rate_amount: float | None = None
    currency: str | None = None
    floor: int | None = None
    size_sqm: float | None = None
    max_guests: int | None = None
    bed_configuration: str | None = None
    accessible: bool = False
    notes: str | None = None
    amenities: list[str] = Field(default_factory=list)
    availability: bool = True
