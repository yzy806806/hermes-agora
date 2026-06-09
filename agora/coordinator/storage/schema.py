"""SQL schema definitions for the Agora Coordinator database."""

SCHEMA_VERSION = 5

SCHEMA_SQL = """\
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hermes_endpoint TEXT,
    model TEXT,
    capabilities TEXT,
    role TEXT DEFAULT 'expert',
    registered_at TEXT NOT NULL,
    is_online INTEGER DEFAULT 0,
    last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS motions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    context TEXT,
    rounds INTEGER NOT NULL DEFAULT 3,
    voting_method TEXT NOT NULL DEFAULT 'simple_majority',
    status TEXT NOT NULL DEFAULT 'draft',
    current_round INTEGER DEFAULT 0,
    decision TEXT,
    rationale TEXT,
    action_items TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    smart_mode INTEGER DEFAULT 1,
    assessment_config TEXT,
    devils_advocate_count INTEGER DEFAULT 0,
    focus_areas TEXT,
    early_vote_triggered INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    round_num INTEGER NOT NULL,
    stance TEXT,
    content TEXT NOT NULL,
    evidence TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    vote TEXT NOT NULL,
    vote_type TEXT NOT NULL DEFAULT 'binary',
    vote_data TEXT,
    confidence REAL,
    reason TEXT,
    timestamp TEXT NOT NULL,
    UNIQUE(motion_id, agent_id),
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_motion ON messages(motion_id);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_round ON messages(motion_id, round_num);
CREATE INDEX IF NOT EXISTS idx_votes_motion ON votes(motion_id);

CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    round INTEGER,
    result TEXT,
    consensus_level TEXT,
    metrics TEXT,
    rationale TEXT,
    created_at TEXT,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assessments_motion ON assessments(motion_id);

CREATE TABLE IF NOT EXISTS judgment_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    predicted TEXT NOT NULL,
    actual TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    is_correct INTEGER NOT NULL DEFAULT 0,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_judgment_agent ON judgment_records(agent_id);
CREATE INDEX IF NOT EXISTS idx_judgment_motion ON judgment_records(motion_id);

-- Bootstrap tables for self-organizing development

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
    decision TEXT NOT NULL,
    rationale TEXT,
    action_items TEXT,
    approval_status TEXT DEFAULT 'pending',
    approved_by TEXT,
    feedback TEXT,
    requested_at TEXT NOT NULL,
    processed_at TEXT,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bootstrap_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT,
    capabilities TEXT,
    active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_bootstrap_triggers_status ON bootstrap_triggers(status);
CREATE INDEX IF NOT EXISTS idx_bootstrap_schedules_enabled ON bootstrap_schedules(enabled);
CREATE INDEX IF NOT EXISTS idx_bootstrap_approvals_motion ON bootstrap_approvals(motion_id);
CREATE INDEX IF NOT EXISTS idx_bootstrap_approvals_status ON bootstrap_approvals(approval_status);

-- Phase 8: Dashboard event log

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    detail TEXT,
    motion_id TEXT,
    agent_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_motion ON events(motion_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
"""
