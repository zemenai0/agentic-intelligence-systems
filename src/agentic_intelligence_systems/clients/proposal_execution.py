"""Proposal execution helpers for interactive clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic_intelligence_systems.clients import backend_normalizers as normalizers
from agentic_intelligence_systems.clients import backend_routes
from agentic_intelligence_systems.clients.backend_api import BackendAPIClient, BackendToolError
from agentic_intelligence_systems.contracts.common import Proposal
from agentic_intelligence_systems.contracts.tools import BookingRecord


@dataclass(slots=True)
class ProposalExecutionResult:
    """Normalized result for an executed proposal."""

    tool_name: str
    raw_result: Any
    booking: BookingRecord | None = None
    service_booking_id: str | None = None
    service_booking_total_cents: int | None = None
    service_name: str | None = None
    service_message: str | None = None


async def execute_proposal(
    backend_client: BackendAPIClient,
    *,
    request_id: str,
    trace_id: str,
    proposal: Proposal,
) -> ProposalExecutionResult:
    """Execute a supported proposal against the backend."""

    if proposal.tool_name == "create_booking":
        raw_result = await backend_client._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.create_booking(
                {
                    "roomId": proposal.arguments["room_id"],
                    "resortId": proposal.arguments["resort_id"],
                    "checkInDate": proposal.arguments["check_in_date"],
                    "checkOutDate": proposal.arguments["check_out_date"],
                    "adults": proposal.arguments["adults"],
                    "children": proposal.arguments["children"],
                    "specialRequests": proposal.arguments.get("special_requests"),
                }
            ),
        )
        booking = normalizers.normalize_booking_record(raw_result)
        service_booking_id = None
        service_booking_total_cents = None
        service_name = proposal.arguments.get("pending_service_name")
        service_message = None
        pending_service_id = proposal.arguments.get("pending_service_id")
        if pending_service_id and booking.booking_id:
            booking_status = (booking.status or "").lower()
            if booking_status in {"confirmed", "checked_in"}:
                try:
                    service_result = await backend_client._request_json(
                        request_id=request_id,
                        trace_id=trace_id,
                        route=backend_routes.create_service_booking(
                            booking.booking_id,
                            {
                                "serviceId": pending_service_id,
                                "quantity": 1,
                                "scheduledAt": proposal.arguments.get("pending_service_scheduled_at"),
                                "notes": (
                                    f"Added during booking flow: {service_name}"
                                    if service_name
                                    else "Added during booking flow"
                                ),
                            },
                        ),
                    )
                    service_booking_id, service_booking_total_cents = _parse_service_booking_result(
                        service_result
                    )
                except BackendToolError:
                    if service_name:
                        service_message = (
                            f"{service_name} could not be finalized yet. "
                            "You can add it after the booking is confirmed."
                        )
            elif service_name:
                if booking_status == "pending":
                    service_message = (
                        f"{service_name} has been booked with your room. "
                    )
                else:
                    service_message = (
                        f"{service_name} has not been booked yet. "
                        "I saved it in the reservation request, and it can be added once the booking is confirmed or checked in."
                    )
        return ProposalExecutionResult(
            tool_name=proposal.tool_name,
            raw_result=raw_result,
            booking=booking,
            service_booking_id=service_booking_id,
            service_booking_total_cents=service_booking_total_cents,
            service_name=service_name,
            service_message=service_message,
        )

    if proposal.tool_name == "create_service_booking":
        booking_id = proposal.arguments["booking_id"]
        raw_result = await backend_client._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.create_service_booking(
                booking_id,
                {
                    "serviceId": proposal.arguments["service_id"],
                    "quantity": proposal.arguments.get("quantity", 1),
                    "scheduledAt": proposal.arguments["scheduled_at"],
                    "notes": proposal.arguments.get("notes"),
                },
            ),
        )
        return ProposalExecutionResult(proposal.tool_name, raw_result)

    if proposal.tool_name == "create_service_request":
        booking_id = proposal.arguments["booking_id"]
        raw_result = await backend_client._request_json(
            request_id=request_id,
            trace_id=trace_id,
            route=backend_routes.create_service_request(
                booking_id,
                {
                    "type": proposal.arguments["type"],
                    "description": proposal.arguments["description"],
                },
            ),
        )
        return ProposalExecutionResult(proposal.tool_name, raw_result)

    raise ValueError(f"Unsupported proposal execution for {proposal.tool_name}.")


def _parse_service_booking_result(payload: Any) -> tuple[str | None, int | None]:
    data = normalizers.unwrap_payload(payload)
    if not isinstance(data, dict):
        return None, None
    service_booking_id = normalizers.pick_value(data, "id", "serviceBookingId")
    total_price_cents = normalizers.pick_value(
        data,
        "totalPriceCents",
        "total_price_cents",
    )
    return (
        str(service_booking_id) if service_booking_id is not None else None,
        int(total_price_cents) if total_price_cents is not None else None,
    )
