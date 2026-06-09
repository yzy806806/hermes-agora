"""SQL schema for Bootstrap tables (Phase 4)."""

BOOTSTRAP_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS bootstrap_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL,
    topic TEXT NOT NULL,
    source TEXT,
    context TEXT,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_bt_status ON bootstrap_triggers(status);
CREATE INDEX IF NOT EXISTS idx_bt_priority ON bootstrap_triggers(priority);

CREATE TABLE IF NOT EXISTS bootstrap_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    topic_template TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    next_run TEXT,
    last_run TEXT
);

CREATE TABLE IF NOT EXISTS bootstrap_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    decision TEXT,
    rationale TEXT,
    action_items TEXT,
    approval_status TEXT DEFAULT 'pending',
    approved_by TEXT,
    feedback TEXT,
    requested_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ba_motion ON bootstrap_approvals(motion_id);
CREATE INDEX IF NOT EXISTS idx_ba_status ON bootstrap_approvals(approval_status);

CREATE TABLE IF NOT EXISTS bootstrap_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT,
    capabilities TEXT,
    active INTEGER DEFAULT 1
);
"""
