"""SQL schema definitions for the Agora Coordinator database."""

SCHEMA_VERSION = 2

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
"""
