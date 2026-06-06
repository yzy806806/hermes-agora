"""Tests for ApprovalFlow module."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coordinator.bootstrap.approval_flow import ApprovalFlow, ApprovalStatus
from coordinator.storage.schema import SCHEMA_SQL


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(loop_scope="module")
async def db_path(tmp_path_factory):
    import aiosqlite
    path = str(tmp_path_factory.mktemp("approval") / "test.db")
    async with aiosqlite.connect(path) as conn:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    yield path


@pytest_asyncio.fixture(loop_scope="module")
async def flow(db_path):
    return ApprovalFlow(db_path)


class TestApprovalStatus:
    def test_values(self):
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"


class TestApprovalFlow:
    @pytest.mark.asyncio
    async def test_submit_for_approval(self, flow):
        aid = await flow.submit_for_approval(
            motion_id="m1", decision="adopted",
            rationale="Good plan", action_items=[{"title": "Build X"}],
        )
        assert aid.isdigit()

    @pytest.mark.asyncio
    async def test_get_approval(self, flow):
        aid = await flow.submit_for_approval(
            motion_id="m2", decision="rejected",
        )
        record = await flow.get_approval(aid)
        assert record is not None
        assert record["motion_id"] == "m2"
        assert record["approval_status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_approval_not_found(self, flow):
        record = await flow.get_approval("999999")
        assert record is None

    @pytest.mark.asyncio
    async def test_get_approval_by_motion(self, flow):
        await flow.submit_for_approval(
            motion_id="m3", decision="adopted",
        )
        record = await flow.get_approval_by_motion("m3")
        assert record is not None
        assert record["motion_id"] == "m3"

    @pytest.mark.asyncio
    async def test_get_approval_by_motion_not_found(self, flow):
        record = await flow.get_approval_by_motion("nonexistent")
        assert record is None

    @pytest.mark.asyncio
    async def test_list_pending(self, flow):
        await flow.submit_for_approval(
            motion_id="m4", decision="adopted",
        )
        pending = await flow.list_pending()
        assert len(pending) >= 1
        assert all(p["approval_status"] == "pending" for p in pending)

    @pytest.mark.asyncio
    async def test_list_all(self, flow, db_path):
        # Insert a fresh record directly to ensure data exists
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT INTO bootstrap_approvals
                   (motion_id, decision, rationale, action_items,
                    approval_status, requested_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ["m_list_all", "adopted", "test", "[]",
                 "pending", "2026-01-01T00:00:00"],
            )
            await db.commit()
        items = await flow.list_all()
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_list_all_filtered(self, flow):
        items = await flow.list_all(status="pending")
        assert all(i["approval_status"] == "pending" for i in items)

    @pytest.mark.asyncio
    async def test_handle_approval_approve(self, flow):
        aid = await flow.submit_for_approval(
            motion_id="m5", decision="adopted",
        )
        result = await flow.handle_approval(
            aid, approved=True, approved_by="alice",
        )
        assert result["status"] == "approved"
        record = await flow.get_approval(aid)
        assert record["approval_status"] == "approved"
        assert record["approved_by"] == "alice"

    @pytest.mark.asyncio
    async def test_handle_approval_reject(self, flow):
        aid = await flow.submit_for_approval(
            motion_id="m6", decision="adopted",
        )
        result = await flow.handle_approval(
            aid, approved=False, feedback="Need more info",
        )
        assert result["status"] == "rejected"
        assert result["feedback"] == "Need more info"
        record = await flow.get_approval(aid)
        assert record["approval_status"] == "rejected"
