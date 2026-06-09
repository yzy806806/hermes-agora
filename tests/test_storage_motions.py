"""Tests for Motion CRUD operations."""

import pytest

from agora.coordinator.storage import Storage


@pytest.mark.asyncio
async def test_create_and_get_motion(storage: Storage):
    result = await storage.create_motion(
        "Test Motion", "Description", rounds=5, voting_method="unanimous"
    )
    assert "id" in result
    motion = await storage.get_motion(result["id"])
    assert motion is not None
    assert motion["title"] == "Test Motion"
    assert motion["rounds"] == 5
    assert motion["voting_method"] == "unanimous"
    assert motion["status"] == "draft"


@pytest.mark.asyncio
async def test_get_motion_not_found(storage: Storage):
    assert await storage.get_motion("nonexistent-id") is None


@pytest.mark.asyncio
async def test_list_motions(storage: Storage):
    m1 = await storage.create_motion("M1", "D1")
    m2 = await storage.create_motion("M2", "D2")
    await storage.update_motion_status(m1["id"], "discussing")

    all_motions = await storage.list_motions()
    assert len(all_motions) == 2

    discussing = await storage.list_motions(status="discussing")
    assert len(discussing) == 1
    assert discussing[0]["id"] == m1["id"]


@pytest.mark.asyncio
async def test_update_motion_status(storage: Storage):
    m = await storage.create_motion("M", "D")
    await storage.update_motion_status(
        m["id"], "closed", decision="adopted", rationale="Good"
    )
    motion = await storage.get_motion(m["id"])
    assert motion["status"] == "closed"
    assert motion["decision"] == "adopted"
    assert motion["rationale"] == "Good"
    assert motion["closed_at"] is not None


@pytest.mark.asyncio
async def test_increment_round(storage: Storage):
    m = await storage.create_motion("M", "D", rounds=3)
    assert (await storage.get_motion(m["id"]))["current_round"] == 0

    r1 = await storage.increment_round(m["id"])
    assert r1 == 1
    assert (await storage.get_motion(m["id"]))["current_round"] == 1

    r2 = await storage.increment_round(m["id"])
    assert r2 == 2
