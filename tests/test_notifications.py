"""Phase 13.4e: Notification WS delivery integration tests.

Validates end-to-end flow: NotificationManager.create() →
DashboardHub.broadcast_event → subscribed WS clients receive
NOTIFICATION messages with correct payload and filtering.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agora.coordinator.dashboard_ws import (
    CHANNEL_NOTIFICATIONS, CHANNEL_EVENTS, DashboardHub,
)
from agora.coordinator.notifications import NotificationManager
from agora.coordinator.token_manager import TokenManager


@pytest.fixture
def token_mgr():
    return TokenManager(secret="test-notif-secret")


@pytest.fixture
def hub(token_mgr):
    h = DashboardHub()
    h.set_token_manager(token_mgr)
    return h


def _mock_storage():
    s = AsyncMock()
    s.create_notification = AsyncMock(return_value={
        "id": "n1", "type": "pipeline_completed",
        "title": "Done", "body": "b", "project_id": "p1",
        "priority": "high", "read": False,
    })
    return s


async def _add_client(hub, token_mgr, cid, channels, projects=None):
    ws = AsyncMock()
    token = token_mgr.create_token(f"u_{cid}", "admin")
    await hub.connect(cid, ws, token)
    hub._clients[cid].subscriptions = set(channels)
    if projects is not None:
        hub._clients[cid].project_subscriptions = set(projects)
    return ws


class TestWSNotificationDelivery:
    @pytest.mark.asyncio
    async def test_notification_pushed_to_subscribed(self, hub, token_mgr):
        """Client subscribed to notifications channel receives NOTIFICATION."""
        ws = await _add_client(
            hub, token_mgr, "c1", channels={CHANNEL_NOTIFICATIONS},
        )
        mgr = NotificationManager(_mock_storage(), dashboard_hub=hub)
        await mgr.create(
            type="pipeline_completed", title="Done",
            body="All tasks passed", project_id="proj1",
        )
        ws.send_json.assert_any_call(
            {"type": "NOTIFICATION", "payload": ws.send_json.call_args[0][0]["payload"]},
        )

    @pytest.mark.asyncio
    async def test_notification_not_sent_to_unsubscribed(self, hub, token_mgr):
        """Client NOT subscribed to notifications channel is skipped."""
        ws = await _add_client(
            hub, token_mgr, "c1", channels={CHANNEL_EVENTS},
        )
        mgr = NotificationManager(_mock_storage(), dashboard_hub=hub)
        notif = await mgr.create(
            type="agent_offline", title="Down",
            body="heartbeat lost", project_id="proj1",
        )
        # The hub broadcast goes to notifications channel only
        # c1 only subscribes to events → should NOT receive NOTIFICATION
        for call in ws.send_json.call_args_list:
            msg = call[0][0]
            assert msg.get("type") != "NOTIFICATION"

    @pytest.mark.asyncio
    async def test_notification_project_filter(self, hub, token_mgr):
        """WS delivery respects project subscription filtering."""
        ws_match = await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_NOTIFICATIONS}, projects={"proj1"},
        )
        ws_no_match = await _add_client(
            hub, token_mgr, "c2",
            channels={CHANNEL_NOTIFICATIONS}, projects={"proj2"},
        )
        mgr = NotificationManager(_mock_storage(), dashboard_hub=hub)
        await mgr.create(
            type="pipeline_failed", title="Failed",
            body="OOM", project_id="proj1",
        )
        # c1 subscribed to proj1 → receives; c2 subscribed to proj2 → skipped
        found = any(
            c[0][0].get("type") == "NOTIFICATION"
            for c in ws_match.send_json.call_args_list
        )
        assert found
        for c in ws_no_match.send_json.call_args_list:
            assert c[0][0].get("type") != "NOTIFICATION"

    @pytest.mark.asyncio
    async def test_notification_no_project_subs_receives_all(
        self, hub, token_mgr,
    ):
        """Client with no project subscriptions receives all notifications."""
        ws = await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_NOTIFICATIONS}, projects=set(),
        )
        mgr = NotificationManager(_mock_storage(), dashboard_hub=hub)
        await mgr.create(
            type="review_requested", title="Review",
            body="Please review", project_id="proj_any",
        )
        found = any(
            c[0][0].get("type") == "NOTIFICATION"
            for c in ws.send_json.call_args_list
        )
        assert found

    @pytest.mark.asyncio
    async def test_broadcast_returns_client_count(self, hub, token_mgr):
        """_push_to_dashboards returns number of clients notified."""
        await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_NOTIFICATIONS}, projects=set(),
        )
        await _add_client(
            hub, token_mgr, "c2",
            channels={CHANNEL_NOTIFICATIONS}, projects=set(),
        )
        mgr = NotificationManager(_mock_storage(), dashboard_hub=hub)
        notif = await mgr.create(
            type="discussion_deadlock", title="Stuck",
            body="No consensus", project_id="p1",
        )
        # Two clients subscribed to notifications, both should be notified
        count = await mgr._push_to_dashboards(notif)
        assert count == 2

    @pytest.mark.asyncio
    async def test_no_hub_returns_zero(self):
        """_push_to_dashboards returns 0 when no hub is set."""
        mgr = NotificationManager(_mock_storage())
        from agora.coordinator.notification_models import Notification, NotificationType, NotificationPriority
        from datetime import datetime, timezone
        notif = Notification(
            id="x", type=NotificationType.AGENT_OFFLINE,
            title="t", body="b", project_id="p",
            priority=NotificationPriority.HIGH,
            created_at=datetime.now(timezone.utc),
        )
        count = await mgr._push_to_dashboards(notif)
        assert count == 0
