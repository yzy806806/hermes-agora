//! Data models shared across the SDK.
//!
//! Client-side AgentConfig + server-returned data models.
//! Matches the Python SDK's `protocol.py` and `models.py`.

use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Configuration for connecting to the Agora Coordinator.
#[derive(Clone, Debug)]
pub struct AgentConfig {
    pub coordinator_url: String,
    pub agent_id: String,
    pub agent_name: String,
    pub agent_type: String,
    pub capabilities: Vec<String>,
    pub model: String,
    pub agent_token: Option<String>,
    pub heartbeat_interval: Duration,
    pub max_retries: u32,
}

impl AgentConfig {
    /// Create a new config with required fields and sensible defaults.
    pub fn new(coordinator_url: &str, agent_name: &str) -> Self {
        Self {
            coordinator_url: coordinator_url.to_string(),
            agent_id: uuid::Uuid::new_v4().to_string(),
            agent_name: agent_name.to_string(),
            agent_type: "custom".to_string(),
            capabilities: Vec::new(),
            model: String::new(),
            agent_token: None,
            heartbeat_interval: Duration::from_secs(30),
            max_retries: 3,
        }
    }

    pub fn with_agent_type(mut self, t: &str) -> Self { self.agent_type = t.into(); self }
    pub fn with_capabilities(mut self, c: Vec<String>) -> Self { self.capabilities = c; self }
    pub fn with_model(mut self, m: &str) -> Self { self.model = m.into(); self }
    pub fn with_token(mut self, t: &str) -> Self { self.agent_token = Some(t.into()); self }
}

/// Per-agent runtime config received in the WELCOME message.
/// Mirrors Python SDK's `AgentConfig` (server-side).
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AgentWelcomeConfig {
    pub agent_id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default = "default_agent_type")]
    pub agent_type: String,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub model: String,
    #[serde(default = "default_max_tasks")]
    pub max_concurrent_tasks: u32,
    #[serde(default = "default_hb_interval")]
    pub heartbeat_interval_seconds: u32,
    #[serde(default = "default_hb_timeout")]
    pub heartbeat_timeout_seconds: u32,
    #[serde(default = "default_tpm_limit")]
    pub tpm_limit: u32,
    #[serde(default = "default_tpm_burst")]
    pub tpm_burst_factor: f64,
    #[serde(default = "default_discussion_roles")]
    pub allowed_discussion_roles: Vec<String>,
    #[serde(default)]
    pub auto_accept_tasks: bool,
}

fn default_agent_type() -> String { "custom".into() }
fn default_max_tasks() -> u32 { 2 }
fn default_hb_interval() -> u32 { 30 }
fn default_hb_timeout() -> u32 { 120 }
fn default_tpm_limit() -> u32 { 10000 }
fn default_tpm_burst() -> f64 { 1.5 }
fn default_discussion_roles() -> Vec<String> { vec!["participant".into()] }
