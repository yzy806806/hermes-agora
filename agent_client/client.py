"""AgoraClient — HTTP + WebSocket client for the Agora Coordinator.

Provides high-level methods that map to the 6 Hermes tools.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import AgoraConfig
from .ws_pool import WSConnection

logger = logging.getLogger(__name__)


class AgoraClient:
    """Client for the Agora Coordinator (HTTP + WebSocket)."""

    def __init__(self, config: AgoraConfig) -> None:
        self._config = config
        self._http = httpx.AsyncClient(
            base_url=config.coordinator_url,
            timeout=config.request_timeout,
        )
        self._ws = WSConnection(config)

    # -- HTTP helpers --------------------------------------------------------

    def _error(self, code: str, message: str, **details: Any) -> dict[str, Any]:
        return {"status": "error", "error_code": code, "message": message, "details": details}

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        try:
            resp = await self._http.get(path, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", str(exc))
            return self._error("COORDINATOR_ERROR", detail)
        except httpx.RequestError as exc:
            return self._error("CONNECTION_FAILED", str(exc))

    async def _post(self, path: str, json: dict) -> dict[str, Any]:
        try:
            resp = await self._http.post(path, json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", str(exc))
            return self._error("COORDINATOR_ERROR", detail)
        except httpx.RequestError as exc:
            return self._error("CONNECTION_FAILED", str(exc))

    # -- Tool methods --------------------------------------------------------

    async def create_motion(
        self, title: str, description: str = "", context: str | None = None,
        rounds: int | None = None, voting_method: str = "simple_majority",
    ) -> dict[str, Any]:
        if not title or len(title) > 200:
            return self._error("INVALID_PARAMS", "title must be 1-200 chars")
        body: dict[str, Any] = {
            "title": title, "description": description,
            "rounds": rounds or self._config.default_rounds,
            "voting_method": voting_method,
        }
        if context is not None:
            body["context"] = context
        result = await self._post("/api/v1/motions", json=body)
        if result.get("status") == "error":
            return result
        # Rename motion status to motion_status to avoid collision
        motion_status = result.pop("status", "draft")
        return {
            "status": "success", "motion_status": motion_status,
            **result, "message": "Motion created successfully",
        }

    async def list_motions(
        self, status: str | None = None, limit: int = 10, offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        result = await self._get("/api/v1/motions", params=params)
        if result.get("status") == "error":
            return result
        return {"status": "success", **result, "message": f"Retrieved motions"}

    async def get_history(
        self, motion_id: str, limit: int = 50, include_votes: bool = True,
    ) -> dict[str, Any]:
        result = await self._get(f"/api/v1/motions/{motion_id}/history")
        if result.get("status") == "error":
            return result
        return {"status": "success", "motion_id": motion_id, **result}

    async def get_result(self, motion_id: str) -> dict[str, Any]:
        result = await self._get(f"/api/v1/motions/{motion_id}/result")
        if result.get("status") == "error":
            return result
        return {"status": "success", "motion_id": motion_id, **result}

    async def speak(
        self, motion_id: str, content: str, stance: str = "neutral",
        evidence: list[dict] | None = None,
    ) -> dict[str, Any]:
        msg = {
            "type": "SPEAK", "motion_id": motion_id,
            "agent_id": self._config.agent_id,
            "payload": {"content": content, "stance": stance, "evidence": evidence or []},
        }
        resp = await self._ws.send_and_wait(msg, timeout=30.0)
        if resp is None:
            return self._error("CONNECTION_FAILED", "WebSocket not connected")
        if resp.get("type") == "ERROR":
            payload = resp.get("payload", {})
            return self._error(payload.get("code", "WS_ERROR"), payload.get("message", ""))
        return {"status": "success", "motion_id": motion_id, "message": "Speech submitted"}

    async def vote(
        self, motion_id: str, vote: str, reason: str = "", confidence: float = 0.5,
    ) -> dict[str, Any]:
        msg = {
            "type": "VOTE", "motion_id": motion_id,
            "agent_id": self._config.agent_id,
            "payload": {"vote": vote, "reason": reason, "confidence": confidence},
        }
        resp = await self._ws.send_and_wait(msg, timeout=30.0)
        if resp is None:
            return self._error("CONNECTION_FAILED", "WebSocket not connected")
        if resp.get("type") == "ERROR":
            payload = resp.get("payload", {})
            return self._error(payload.get("code", "WS_ERROR"), payload.get("message", ""))
        return {"status": "success", "motion_id": motion_id, "vote": vote, "message": "Vote submitted"}

    # -- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        await self._ws.close()
        await self._http.aclose()
