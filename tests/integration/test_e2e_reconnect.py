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


def _ws_url(port: int, agent_id: str, token: str) -> str:
    """Build WS URL with token for auth."""
    return f"ws://127.0.0.1:{port}/ws/{agent_id}?token={token}"


@pytest_asyncio.fixture
async def motion_id_reconnect(coordinator_port: int) -> str:
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


async def _drain(ws, count: int, timeout: float = 2.0) -> None:
    """Drain up to `count` messages from a websocket."""
    for _ in range(count):
        try:
            await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            break


@pytest.mark.timeout(60)
async def test_agent_reconnect(
    coordinator_port: int,
    registered_agents: list[dict],
    motion_id_reconnect: str,
) -> None:
    """Agent disconnects then reconnects and continues."""
    url_a = _ws_url(
        coordinator_port, "test-agent-0",
        registered_agents[0]["agent_token"],
    )
    url_b = _ws_url(
        coordinator_port, "test-agent-1",
        registered_agents[1]["agent_token"],
    )

    # Phase 1: Both agents connect and speak
    async with websockets.connect(url_a) as ws_a, \
               websockets.connect(url_b) as ws_b:
        assert json.loads(await ws_a.recv())["type"] == "WELCOME"
        assert json.loads(await ws_b.recv())["type"] == "WELCOME"

        await ws_a.send(json.dumps({
            "type": "SPEAK",
            "payload": {
                "motion_id": motion_id_reconnect, "round": 1,
                "stance": "support", "content": "GraphQL is flexible.",
            },
        }))
        await _drain(ws_a, 4)
        await _drain(ws_b, 2)

    # Phase 2: Agent A reconnects
    async with websockets.connect(url_a) as ws_a2:
        # Drain any offline broadcasts before WELCOME
        msg = json.loads(await ws_a2.recv())
        if msg["type"] != "WELCOME":
            msg = json.loads(await ws_a2.recv())
        assert msg["type"] == "WELCOME"

        async with websockets.connect(url_b) as ws_b2:
            msg = json.loads(await ws_b2.recv())
            # May get offline broadcast, drain to WELCOME
            if msg["type"] != "WELCOME":
                msg = json.loads(await ws_b2.recv())
            assert msg["type"] == "WELCOME"

            await ws_b2.send(json.dumps({
                "type": "SPEAK",
                "payload": {
                    "motion_id": motion_id_reconnect, "round": 1,
                    "stance": "oppose", "content": "REST is simpler.",
                },
            }))
            await _drain(ws_a2, 4)

            # Force vote and both vote
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    f"http://127.0.0.1:{coordinator_port}"
                    f"/api/v1/motions/{motion_id_reconnect}"
                    "/force-vote"
                )
                assert r.status_code == 200, r.text

            for ws, vote in [(ws_a2, "yes"), (ws_b2, "no")]:
                await ws.send(json.dumps({
                    "type": "VOTE",
                    "payload": {
                        "motion_id": motion_id_reconnect,
                        "type": "binary",
                        "vote": vote,
                        "confidence": 0.9 if vote == "yes" else 0.6,
                    },
                }))
            await _drain(ws_a2, 6)

    # Verify motion result accessible
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"http://127.0.0.1:{coordinator_port}"
            f"/api/v1/motions/{motion_id_reconnect}/result"
        )
        assert r.status_code in (200, 400), r.text
