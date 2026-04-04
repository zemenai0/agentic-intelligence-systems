"""Admin CLI for live backend maintenance tasks."""

from __future__ import annotations

import argparse
import asyncio
import json

import httpx

from agentic_intelligence_systems.cli.inventory_seed import (
    SeedResult,
    build_demo_room_payloads,
)
from agentic_intelligence_systems.config import get_settings


def main() -> None:
    """Run the admin CLI."""

    parser = argparse.ArgumentParser(prog="habitalife-admin")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed-demo-rooms")
    seed_parser.add_argument("--resort-id", required=True)
    seed_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    if args.command == "seed-demo-rooms":
        asyncio.run(seed_demo_rooms(args.resort_id, dry_run=args.dry_run))


async def seed_demo_rooms(resort_id: str, *, dry_run: bool) -> None:
    """Create demo rooms for a resort using backend admin routes."""

    settings = get_settings()
    if not settings.backend_session_cookie:
        raise RuntimeError("BACKEND_SESSION_COOKIE is required for admin inventory writes.")

    headers = {
        "content-type": "application/json",
        "cookie": settings.backend_session_cookie,
    }
    payloads = build_demo_room_payloads(resort_id)

    async with httpx.AsyncClient(
        base_url=settings.backend_base_url,
        timeout=settings.backend_timeout_seconds,
    ) as client:
        existing_numbers = await load_existing_room_numbers(client, headers, resort_id)
        result = SeedResult()

        for payload in payloads:
            room_number = str(payload["roomNumber"])
            if room_number in existing_numbers:
                result.skipped.append(room_number)
                continue
            if dry_run:
                result.created.append(room_number)
                continue

            response = await client.post("/api/admin/rooms", headers=headers, json=payload)
            if response.is_success:
                result.created.append(room_number)
                continue
            error_text = response.text.strip() or f"HTTP {response.status_code}"
            result.failed.append(f"{room_number}: {error_text}")

    render_seed_result(resort_id, result, dry_run=dry_run, payloads=payloads)


async def load_existing_room_numbers(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    resort_id: str,
) -> set[str]:
    """Return current room numbers for a resort."""

    response = await client.get(
        "/api/admin/rooms",
        headers=headers,
        params={"page": 1, "limit": 100, "resortId": resort_id},
    )
    response.raise_for_status()
    payload = response.json()
    rooms = payload.get("data") if isinstance(payload, dict) else []
    return {
        str(room.get("roomNumber"))
        for room in rooms
        if isinstance(room, dict) and room.get("roomNumber") is not None
    }


def render_seed_result(
    resort_id: str,
    result: SeedResult,
    *,
    dry_run: bool,
    payloads: list[dict[str, object]],
) -> None:
    """Print a concise seed summary."""

    print(f"Resort: {resort_id}")
    if dry_run:
        print("Dry run payloads:")
        print(json.dumps(payloads, indent=2))
    if result.created:
        label = "would create" if dry_run else "created"
        print(f"{label}: {', '.join(result.created)}")
    if result.skipped:
        print(f"skipped existing: {', '.join(result.skipped)}")
    if result.failed:
        print("failed:")
        for item in result.failed:
            print(f"  - {item}")
