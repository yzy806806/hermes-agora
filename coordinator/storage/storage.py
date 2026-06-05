"""SQLite storage layer for the Agora Coordinator service.

Provides the Storage class that manages database connections and
delegates CRUD operations to sub-modules.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite

from . import agents as _agents
from . import messages as _messages
from . import motions as _motions
from . import votes as _votes
from .schema import SCHEMA_SQL, SCHEMA_VERSION

logger = logging.getLogger(__name__)


class Storage:
    """SQLite storage layer with async connection management."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @asynccontextmanager
    async def _connection(self):
        """Async database connection context manager with WAL mode."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_db(self) -> None:
        """Initialize database tables and schema version tracking."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA_SQL)
            await db.execute(
                """CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY, applied_at TEXT)"""
            )
            await db.execute(
                "INSERT OR IGNORE INTO schema_version VALUES (?, ?)",
                [SCHEMA_VERSION, __import__("datetime").datetime.utcnow().isoformat()],
            )
            await db.commit()
        logger.info("Database initialized at %s", self.db_path)

    # --- Agent CRUD ---

    async def register_agent(self, agent_id: str, name: str, model: str,
                             hermes_endpoint: str = "",
                             capabilities: list[str] | None = None,
                             role: str = "expert") -> dict:
        async with self._connection() as db:
            return await _agents.register_agent(
                db, agent_id, name, model, hermes_endpoint, capabilities, role)

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        async with self._connection() as db:
            return await _agents.get_agent(db, agent_id)

    async def list_agents(self, online_only: bool = False) -> list[dict]:
        async with self._connection() as db:
            return await _agents.list_agents(db, online_only)

    async def set_agent_online(self, agent_id: str, online: bool) -> None:
        async with self._connection() as db:
            await _agents.set_agent_online(db, agent_id, online)

    async def deregister_agent(self, agent_id: str) -> None:
        async with self._connection() as db:
            await _agents.deregister_agent(db, agent_id)

    # --- Motion CRUD ---

    async def create_motion(self, title: str, description: str,
                            rounds: int = 3,
                            voting_method: str = "simple_majority",
                            context: str = "") -> dict:
        async with self._connection() as db:
            return await _motions.create_motion(
                db, title, description, rounds, voting_method, context)

    async def get_motion(self, motion_id: str) -> Optional[dict]:
        async with self._connection() as db:
            return await _motions.get_motion(db, motion_id)

    async def list_motions(self, status: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> list[dict]:
        async with self._connection() as db:
            return await _motions.list_motions(db, status, limit, offset)

    async def update_motion_status(self, motion_id: str, status: str,
                                   decision: Optional[str] = None,
                                   rationale: Optional[str] = None,
                                   action_items: Optional[list[str]] = None) -> None:
        async with self._connection() as db:
            await _motions.update_motion_status(
                db, motion_id, status, decision, rationale, action_items)

    async def increment_round(self, motion_id: str) -> int:
        async with self._connection() as db:
            return await _motions.increment_round(db, motion_id)

    # --- Message CRUD ---

    async def add_message(self, motion_id: str, agent_id: str,
                          round_num: int, stance: str, content: str,
                          evidence: list[dict] | None = None) -> int:
        async with self._connection() as db:
            return await _messages.add_message(
                db, motion_id, agent_id, round_num, stance, content, evidence)

    async def get_messages(self, motion_id: str,
                           round_num: Optional[int] = None,
                           agent_id: Optional[str] = None) -> list[dict]:
        async with self._connection() as db:
            return await _messages.get_messages(db, motion_id, round_num, agent_id)

    async def count_messages_by_round(self, motion_id: str,
                                      round_num: int) -> int:
        async with self._connection() as db:
            return await _messages.count_messages_by_round(db, motion_id, round_num)

    # --- Vote CRUD ---

    async def add_vote(self, motion_id: str, agent_id: str, vote: str,
                       confidence: float = 1.0,
                       reason: Optional[str] = None) -> int:
        async with self._connection() as db:
            return await _votes.add_vote(
                db, motion_id, agent_id, vote, confidence, reason)

    async def get_votes(self, motion_id: str) -> list[dict]:
        async with self._connection() as db:
            return await _votes.get_votes(db, motion_id)

    async def has_voted(self, motion_id: str, agent_id: str) -> bool:
        async with self._connection() as db:
            return await _votes.has_voted(db, motion_id, agent_id)

    async def count_votes(self, motion_id: str) -> dict[str, int]:
        async with self._connection() as db:
            return await _votes.count_votes(db, motion_id)

    async def get_vote_summary(self, motion_id: str) -> dict:
        async with self._connection() as db:
            return await _votes.get_vote_summary(db, motion_id)

    # --- Statistics ---

    async def get_active_motion_count(self) -> int:
        async with self._connection() as db:
            return await _votes.get_active_motion_count(db)

    async def get_participant_count(self) -> int:
        async with self._connection() as db:
            return await _votes.get_participant_count(db)
