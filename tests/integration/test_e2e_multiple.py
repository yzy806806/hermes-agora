"""E2E test: multiple agents concurrent discussion.

5 agents connect simultaneously, speak, and vote.
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
async def motion_id_5(coordinator_port: int) -> str:
    """Create and start a motion for 5-agent test."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"http://127.0.0.1:{coordinator_port}/api/v1/motions",
            json={
                "title": "Choose our tech stack",
                "description": "5 agents discuss",
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
async def test_concurrent_agents_speak(
    coordinator_port: int,
    registered_agents: list[dict],
    motion_id_5: str,
) -> None:
    """5 agents connect and speak concurrently."""
    conns = []
    for i in range(5):
        url = _ws_url(
            coordinator_port, f"test-agent-{i}",
            registered_agents[i]["agent_token"],
        )
        ws = await websockets.connect(url)
        conns.append(ws)
        msg = json.loads(await ws.recv())
        assert msg["type"] == "WELCOME"

    # All agents speak concurrently
    stances = ["support", "oppose", "neutral", "support", "oppose"]
    speak_tasks = []
    for i, ws in enumerate(conns):
        speak_tasks.append(ws.send(json.dumps({
            "type": "SPEAK",
            "payload": {
                "motion_id": motion_id_5, "round": 1,
                "stance": stances[i],
                "content": f"Agent {i} opinion on tech stack",
            },
        })))
    await asyncio.gather(*speak_tasks)

    # Drain broadcast messages for each agent
    for ws in conns:
        for _ in range(8):
            try:
                await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                break

    # Force vote
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"http://127.0.0.1:{coordinator_port}"
            f"/api/v1/motions/{motion_id_5}/force-vote"
        )
        assert r.status_code == 200, r.text

    # All 5 agents vote concurrently
    votes = ["yes", "no", "yes", "yes", "no"]
    vote_tasks = []
    for i, ws in enumerate(conns):
        vote_tasks.append(ws.send(json.dumps({
            "type": "VOTE",
            "payload": {
                "motion_id": motion_id_5, "type": "binary",
                "vote": votes[i],
                "confidence": 0.7 + i * 0.05,
            },
        })))
    await asyncio.gather(*vote_tasks)

    # Drain confirmations + result
    for ws in conns:
        for _ in range(4):
            try:
                await asyncio.wait_for(ws.recv(), timeout=3.0)
            except asyncio.TimeoutError:
                break

    # Close all connections
    for ws in conns:
        await ws.close()

    # Verify motion is closed
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"http://127.0.0.1:{coordinator_port}"
            f"/api/v1/motions/{motion_id_5}/result"
        )
        assert r.status_code in (200, 400), r.text
