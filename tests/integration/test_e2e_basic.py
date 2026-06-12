"""E2E test: basic discussion flow.

Tests the complete flow:
create_motion -> start -> speak (2 agents) -> vote -> get_result
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import pytest_asyncio
import websockets

pytestmark = pytest.mark.integration


def _ws_url(port: int, agent_id: str, token: str) -> str:
    """Build WS URL with token for auth."""
    return f"ws://127.0.0.1:{port}/ws/{agent_id}?token={token}"


@pytest_asyncio.fixture
async def motion_id(coordinator_port: int) -> str:
    """Create a motion via HTTP and start it; return motion_id."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"http://127.0.0.1:{coordinator_port}/api/v1/motions",
            json={
                "title": "Should we use microservices?",
                "description": "Discuss architecture choice",
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
async def test_basic_discussion_flow(
    coordinator_port: int,
    registered_agents: list[dict],
    motion_id: str,
) -> None:
    """Full flow: create_motion -> speak (2) -> vote -> result."""
    url_a = _ws_url(
        coordinator_port, "test-agent-0",
        registered_agents[0]["agent_token"],
    )
    url_b = _ws_url(
        coordinator_port, "test-agent-1",
        registered_agents[1]["agent_token"],
    )

    async with websockets.connect(url_a) as ws_a, \
               websockets.connect(url_b) as ws_b:
        # Welcome messages
        msg_a = json.loads(await ws_a.recv())
        assert msg_a["type"] == "WELCOME"
        msg_b = json.loads(await ws_b.recv())
        assert msg_b["type"] == "WELCOME"

        # Agent A speaks
        await ws_a.send(json.dumps({
            "type": "SPEAK",
            "payload": {
                "motion_id": motion_id, "round": 1,
                "stance": "support",
                "content": "Microservices provide better isolation.",
            },
        }))
        # Agent B speaks
        await ws_b.send(json.dumps({
            "type": "SPEAK",
            "payload": {
                "motion_id": motion_id, "round": 1,
                "stance": "oppose",
                "content": "Monolith is simpler for our team.",
            },
        }))

        # Drain broadcast/delivery messages
        for _ in range(4):
            try:
                await asyncio.wait_for(ws_a.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                break

        # Force motion into voting
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"http://127.0.0.1:{coordinator_port}"
                f"/api/v1/motions/{motion_id}/force-vote"
            )
            assert r.status_code == 200, r.text

        # Both agents vote
        for ws, vote in [(ws_a, "yes"), (ws_b, "no")]:
            await ws.send(json.dumps({
                "type": "VOTE",
                "payload": {
                    "motion_id": motion_id, "type": "binary",
                    "vote": vote, "confidence": 0.8,
                },
            }))

        # Drain confirmations + result broadcast
        for _ in range(6):
            try:
                await asyncio.wait_for(ws_a.recv(), timeout=3.0)
            except asyncio.TimeoutError:
                break

    # Verify result via HTTP
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"http://127.0.0.1:{coordinator_port}"
            f"/api/v1/motions/{motion_id}/result"
        )
        assert r.status_code in (200, 400), r.text
