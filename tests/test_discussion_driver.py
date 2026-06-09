"""Tests for DiscussionDriver module."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agora.coordinator.bootstrap.discussion_driver import (
    DiscussionConfig, DiscussionDriver, DiscussionResult,
)


class TestDiscussionConfig:
    def test_defaults(self):
        cfg = DiscussionConfig(motion_title="T", motion_description="D")
        assert cfg.voting_method == "ranked_choice"
        assert cfg.max_rounds == 5
        assert cfg.auto_approve_threshold == 0.8
        assert cfg.participants == []

    def test_custom(self):
        cfg = DiscussionConfig(
            motion_title="T", motion_description="D",
            participants=["a", "b"],
            voting_method="simple_majority", max_rounds=3,
        )
        assert len(cfg.participants) == 2


class TestDiscussionResult:
    def test_defaults(self):
        r = DiscussionResult(motion_id="m1", decision="adopted")
        assert r.recommended_actions == []
        assert r.confidence == 0.0
        assert r.rationale == ""
        assert r.created_at is not None


class TestDiscussionDriver:
    def setup_method(self):
        self.driver = DiscussionDriver("http://localhost:8000")

    def test_url_trailing_slash_stripped(self):
        d = DiscussionDriver("http://localhost:8000/")
        assert d.coordinator_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_create_motion_success(self):
        resp = AsyncMock()
        resp.status = 200
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value={"id": "motion_1"})

        post_cm = MagicMock()
        post_cm.__aenter__ = AsyncMock(return_value=resp)
        post_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.post = MagicMock(return_value=post_cm)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agora.coordinator.bootstrap.discussion_driver.aiohttp.ClientSession",
            return_value=session,
        ):
            mid = await self.driver._create_motion("T", "D", "rc")
            assert mid == "motion_1"

    @pytest.mark.asyncio
    async def test_create_motion_failure(self):
        import aiohttp
        resp = AsyncMock()
        resp.status = 500
        resp.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(),
                status=500, message="Error",
            )
        )

        post_cm = MagicMock()
        post_cm.__aenter__ = AsyncMock(return_value=resp)
        post_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.post = MagicMock(return_value=post_cm)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agora.coordinator.bootstrap.discussion_driver.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(RuntimeError, match="Motion creation failed"):
                await self.driver._create_motion("T", "D", "rc")

    @pytest.mark.asyncio
    async def test_check_motion_closed(self):
        resp = AsyncMock()
        resp.status = 200
        resp.json = AsyncMock(return_value={
            "status": "closed", "decision": "adopted",
            "confidence": 0.9, "rationale": "Good",
        })

        get_cm = MagicMock()
        get_cm.__aenter__ = AsyncMock(return_value=resp)
        get_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.get = MagicMock(return_value=get_cm)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agora.coordinator.bootstrap.discussion_driver.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await self.driver._check_motion_status("m1")
            assert result is not None
            assert result.decision == "adopted"

    @pytest.mark.asyncio
    async def test_cancel_discussion(self):
        resp = AsyncMock()
        resp.status = 204

        del_cm = MagicMock()
        del_cm.__aenter__ = AsyncMock(return_value=resp)
        del_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.delete = MagicMock(return_value=del_cm)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "agora.coordinator.bootstrap.discussion_driver.aiohttp.ClientSession",
            return_value=session,
        ):
            ok = await self.driver.cancel_discussion("m1")
            assert ok is True
