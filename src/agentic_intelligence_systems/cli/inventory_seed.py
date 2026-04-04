"""Inventory seed helpers for admin CLI commands."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SeedResult:
    """Result summary for demo room seeding."""

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def build_demo_room_payloads(resort_id: str) -> list[dict[str, object]]:
    """Return realistic demo rooms for a single resort."""

    return [
        {
            "resortId": resort_id,
            "roomNumber": "201",
            "type": "deluxe",
            "floor": 2,
            "sizeSqm": "48.0",
            "maxGuests": 3,
            "bedConfiguration": "1 King",
            "basePriceCents": 32000,
            "accessible": False,
            "notes": "Balcony with garden view",
        },
        {
            "resortId": resort_id,
            "roomNumber": "202",
            "type": "superior",
            "floor": 2,
            "sizeSqm": "42.0",
            "maxGuests": 2,
            "bedConfiguration": "1 Queen",
            "basePriceCents": 28000,
            "accessible": False,
            "notes": "Quiet wing near the spa",
        },
        {
            "resortId": resort_id,
            "roomNumber": "301",
            "type": "suite",
            "floor": 3,
            "sizeSqm": "65.0",
            "maxGuests": 4,
            "bedConfiguration": "1 King + Sofa Bed",
            "basePriceCents": 45000,
            "accessible": True,
            "notes": "Family suite with lake-facing lounge area",
        },
    ]
