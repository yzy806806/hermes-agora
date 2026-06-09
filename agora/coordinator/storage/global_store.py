"""Global SQLite storage for tenant registry (Phase 8.2).

Manages the global.db that stores the list of all tenants.
Each tenant's actual data lives in its own per-tenant agora.db.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

GLOBAL_SCHEMA_SQL = """\
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active);
"""


class GlobalStorage:
    """Manages the global.db tenant registry."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    async def init_db(self) -> None:
        """Create global.db and tenants table if not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.executescript(GLOBAL_SCHEMA_SQL)
            await db.commit()
        logger.info("Global DB initialized at %s", self.db_path)

    async def create_tenant(self, tenant_id: str, name: str,
                            config: dict) -> dict:
        """Insert a new tenant row into global.db."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute(
                "INSERT INTO tenants VALUES (?, ?, ?, ?, 1)",
                [tenant_id, name, json.dumps(config), now],
            )
            await db.commit()
        return {"tenant_id": tenant_id, "name": name,
                "config": config, "created_at": now, "is_active": 1}

    async def get_tenant(self, tenant_id: str) -> Optional[dict]:
        """Get a single tenant by ID."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tenants WHERE tenant_id = ? AND is_active = 1",
                [tenant_id],
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)

    async def list_tenants(self) -> list[dict]:
        """List all active tenants."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tenants WHERE is_active = 1"
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Soft-delete a tenant (set is_active=0)."""
        async with aiosqlite.connect(str(self.db_path)) as db:
            cursor = await db.execute(
                "UPDATE tenants SET is_active = 0 WHERE tenant_id = ?",
                [tenant_id],
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict:
        d = dict(row)
        if "config" in d and isinstance(d["config"], str):
            d["config"] = json.loads(d["config"])
        return d
