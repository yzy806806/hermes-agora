//! Session and artifact API types.
//!
//! Mirrors the Python SDK's `models.py` session models.

use serde::{Deserialize, Serialize};

/// Filter parameters for querying session records.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SessionFilter {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub project_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub outcome: Option<String>,
    #[serde(default = "default_limit")]
    pub limit: u32,
    #[serde(default)]
    pub offset: u32,
}

impl Default for SessionFilter {
    fn default() -> Self {
        Self {
            agent_id: None,
            project_id: None,
            session_type: None,
            outcome: None,
            limit: default_limit(),
            offset: 0,
        }
    }
}

fn default_limit() -> u32 {
    20
}

/// A persisted session record.
/// Matches the Python SDK's `SessionRecord` model.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SessionRecord {
    #[serde(default)]
    pub id: String,
    pub agent_id: String,
    #[serde(default)]
    pub project_id: String,
    #[serde(default = "default_session_type")]
    pub session_type: String,
    pub started_at: String,
    pub ended_at: Option<String>,
    #[serde(default)]
    pub input_messages: Vec<serde_json::Value>,
    #[serde(default)]
    pub output_messages: Vec<serde_json::Value>,
    #[serde(default)]
    pub tool_calls: Vec<serde_json::Value>,
    #[serde(default)]
    pub errors: Vec<serde_json::Value>,
    #[serde(default = "default_outcome")]
    pub outcome: String,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

fn default_session_type() -> String {
    "task_execution".into()
}
fn default_outcome() -> String {
    "success".into()
}

/// A note attached to a session by an agent.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SessionNote {
    pub content: String,
    #[serde(default)]
    pub tags: Vec<String>,
    pub created_at: String,
}
