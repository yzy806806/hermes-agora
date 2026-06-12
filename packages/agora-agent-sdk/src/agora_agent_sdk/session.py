"""SessionStore — agent-side session record persistence.

Provides methods to record, query, and annotate sessions via
the Agora Coordinator's REST session API.

Also includes a local file-based fallback for offline use.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from .models import SessionFilter, SessionNote, SessionRecord

logger = logging.getLogger(__name__)

_SESSIONS_PATH = "/api/v1/sessions"


class SessionStore:
    """Agent-side session persistence backed by Agora Coordinator.

    Usage::

        store = SessionStore(
            coordinator_url="http://localhost:8000",
            agent_id="my-agent",
            agent_token="tok_abc123",
        )
        await store.record_session(session)
        sessions = await store.query_sessions(agent_id="my-agent")
    """

    def __init__(
        self,
        coordinator_url: str,
        agent_id: str,
        agent_token: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = coordinator_url.rstrip("/")
        self._agent_id = agent_id
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if agent_token:
            self._headers["Authorization"] = f"Bearer {agent_token}"
        self._timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
        )

    async def record_session(self, session: SessionRecord) -> None:
        """Record a session (POST /api/v1/sessions)."""
        async with self._client() as client:
            resp = await client.post(
                _SESSIONS_PATH, json=session.model_dump(mode="json")
            )
            resp.raise_for_status()
        logger.info("Recorded session %s", session.id)

    async def query_sessions(
        self,
        _filter: Optional[SessionFilter] = None,
        **kwargs: object,
    ) -> list[SessionRecord]:
        """Query sessions (GET /api/v1/sessions?...).

        Accepts a SessionFilter or keyword arguments.
        """
        filt = _filter or SessionFilter(**kwargs)  # type: ignore[arg-type]
        params = filt.model_dump(exclude_none=True, mode="json")
        async with self._client() as client:
            resp = await client.get(_SESSIONS_PATH, params=params)
            resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else data.get("sessions", [])
        return [SessionRecord(**s) for s in items]

    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get a session by ID (GET /api/v1/sessions/{id})."""
        async with self._client() as client:
            resp = await client.get(f"{_SESSIONS_PATH}/{session_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        return SessionRecord(**resp.json())

    async def add_note(self, session_id: str, note: SessionNote) -> None:
        """Add a note to a session (POST /api/v1/sessions/{id}/notes)."""
        async with self._client() as client:
            resp = await client.post(
                f"{_SESSIONS_PATH}/{session_id}/notes",
                json=note.model_dump(mode="json"),
            )
            resp.raise_for_status()
        logger.info("Added note to session %s", session_id)
