//! REST API result models returned by the Coordinator.
//!
//! Matches the Python SDK's result models in `protocol.py`.

use serde::{Deserialize, Serialize};

/// Result of agent registration.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RegistrationResult {
    #[serde(default)]
    pub agent_id: String,
    #[serde(default)]
    pub token: String,
    #[serde(default = "default_ok")]
    pub status: String,
    #[serde(default)]
    pub message: String,
    #[serde(default)]
    pub agent_token: String,
}

/// Result of creating a motion.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MotionResult {
    pub motion_id: String,
    #[serde(default = "default_ok")]
    pub status: String,
    #[serde(default)]
    pub message: String,
}

/// Result of speaking in a discussion.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SpeechResult {
    #[serde(default = "default_true")]
    pub success: bool,
    #[serde(default)]
    pub message: String,
}

/// Result of voting on a motion.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct VoteResult {
    #[serde(default = "default_true")]
    pub success: bool,
    #[serde(default)]
    pub confirmed: bool,
    #[serde(default)]
    pub message: String,
}

/// A task node in the Agora task graph.
/// Mirrors the Python SDK's `TaskNode` model.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TaskNode {
    #[serde(rename = "task_id")]
    pub id: String,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub description: String,
    pub parent_id: Option<String>,
    #[serde(default)]
    pub priority: u32,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub artifact_paths: Vec<String>,
    #[serde(default)]
    pub created_at: String,
}

fn default_ok() -> String {
    "ok".into()
}
fn default_true() -> bool {
    true
}
