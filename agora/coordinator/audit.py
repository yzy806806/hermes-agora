"""Audit logging for the Agora Coordinator (Phase 10.2c).

Records security-relevant events for compliance and debugging.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import aiosqlite
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Categories of audit events."""

    AUTH = "auth"
    AGENT = "agent"
    PERMISSION = "permission"
    TOKEN = "token"
    ADMIN = "admin"
    SYSTEM = "system"


class AuditEvent(BaseModel):
    """A single audit log entry."""

    event_type: AuditEventType
    actor_id: str
    actor_role: str = ""
    action: str
    resource: str = ""
    details: dict = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tenant_id: str = "default"


class AuditLogger:
    """Records and queries security-relevant audit events."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def log_event(self, event: AuditEvent) -> int:
        """Write an audit event to the audit_log table."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO audit_log
                   (event_type, actor_id, actor_role, action,
                    resource, details_json, timestamp, tenant_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    event.event_type.value,
                    event.actor_id,
                    event.actor_role,
                    event.action,
                    event.resource,
                    json.dumps(event.details),
                    event.timestamp.isoformat(),
                    event.tenant_id,
                ],
            )
            row_id = cursor.lastrowid or 0
            await db.commit()
            logger.info(
                "Audit: %s %s by %s on %s",
                event.action, event.event_type.value,
                event.actor_id, event.resource,
            )
            return row_id

    async def query_events(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Search audit log with filters."""
        clauses: list[str] = []
        params: list = []

        if actor_id is not None:
            clauses.append("actor_id = ?")
            params.append(actor_id)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type.value)
        if tenant_id is not None:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if until is not None:
            clauses.append("timestamp <= ?")
            params.append(until.isoformat())

        where = " AND ".join(clauses) if clauses else "1=1"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM audit_log WHERE {where} "
                f"ORDER BY timestamp DESC LIMIT ?",
                params,
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
