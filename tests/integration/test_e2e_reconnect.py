"""E2E test: agent disconnect and reconnect.

Tests that an agent can disconnect and reconnect
to the Coordinator, and resume participation.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import pytest_asyncio
import websockets

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def motion_id_reconnect(
    coordinator_port: int,
) -> str:
    """Create and start a motion for reconnect test."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"http://127.0.0.1:{coordinator_port}/api/v1/motions",
            json={
                "title": "Should we adopt GraphQL?",
                "description": "Reconnect test discussion",
                "rounds": 1,
            },
        )
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        r2 = await c.post(
            f"http://127.0.0.1:{coordinator_port}"
            f"/api/v1/motions/{mid}/start"
        )
        assert r2.status_code == 200, r2.text
        return mid


@pytest.mark.timeout(60)
async def test_agent_reconnect(
    coordinator_port: int,
    registered_agents: list[dict],
    motion_id_reconnect: str,
) -> None:
    """Agent disconnects then reconnects and continues."""
    url_a = f"ws://127.0.0.1:{coordinator_port}/ws/test-agent-0"
    url_b = f"ws://127.0.0.1:{coordinator_port}/ws/test-agent-1"

    # Phase 1: Both agents connect and speak
    async with websockets.connect(url_a) as ws_a, \
               websockets.connect(url_b) as ws_b:
        # Welcome
        msg = json.loads(await ws_a.recv())
        assert msg["type"] == "WELCOME"
        msg = json.loads(await ws_b.recv())
        assert msg["type"] == "WELCOME"

        # Agent A speaks
        await ws_a.send(json.dumps({
            "type": "SPEAK",
            "payload": {
                "motion_id": motion_id_reconnect,
                "round": 1,
                "stance": "support",
                "content": "GraphQL is flexible.",
            },
        }))

        # Drain broadcasts
        for _ in range(4):
            try:
                await asyncio.wait_for(
                    ws_a.recv(), timeout=2.0
                )
            except asyncio.TimeoutError:
                break
        for _ in range(2):
            try:
                await asyncio.wait_for(
                    ws_b.recv(), timeout=2.0
                )
            except asyncio.TimeoutError:
                break

    # Agent A is now disconnected
    # Phase 2: Agent A reconnects
    async with websockets.connect(url_a) as ws_a2:
        msg = json.loads(await ws_a2.recv())
        assert msg["type"] == "WELCOME"

        # Agent B speaks after reconnect
        async with websockets.connect(url_b) as ws_b2:
            msg = json.loads(await ws_b2.recv())
            assert msg["type"] == "WELCOME"

            await ws_b2.send(json.dumps({
                "type": "SPEAK",
                "payload": {
                    "motion_id": motion_id_reconnect,
                    "round": 1,
                    "stance": "oppose",
                    "content": "REST is simpler.",
                },
            }))

            # Drain broadcasts
            for _ in range(4):
                try:
                    await asyncio.wait_for(
                        ws_a2.recv(), timeout=2.0
                    )
                except asyncio.TimeoutError:
                    break

            # Force vote and both vote
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    f"http://127.0.0.1:{coordinator_port}"
                    f"/api/v1/motions/{motion_id_reconnect}"
                    "/force-vote"
                )
                assert r.status_code == 200, r.text

            # Both vote after reconnect
            await ws_a2.send(json.dumps({
                "type": "VOTE",
                "payload": {
                    "motion_id": motion_id_reconnect,
                    "type": "binary",
                    "vote": "yes",
                    "confidence": 0.9,
                },
            }))
            await ws_b2.send(json.dumps({
                "type": "VOTE",
                "payload": {
                    "motion_id": motion_id_reconnect,
                    "type": "binary",
                    "vote": "no",
                    "confidence": 0.6,
                },
            }))

            # Drain confirmations + result
            for _ in range(6):
                try:
                    await asyncio.wait_for(
                        ws_a2.recv(), timeout=3.0
                    )
                except asyncio.TimeoutError:
                    break

    # Verify motion result accessible
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"http://127.0.0.1:{coordinator_port}"
            f"/api/v1/motions/{motion_id_reconnect}/result"
        )
        assert r.status_code in (200, 400), r.text
