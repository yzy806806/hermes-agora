//! Protocol types — WebSocket message types and WS envelope.
//!
//! MessageType variants match the Python SDK's `MessageType` enum.
//! WSMessage is the generic envelope used for all WS communication.

use serde::{Deserialize, Serialize};

/// WebSocket message type constants.
/// Agent → Coordinator variants are listed first, then Coordinator → Agent.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum MessageType {
    // Agent → Coordinator
    Register,
    Deregister,
    Speak,
    RequestSpeak,
    Vote,
    Heartbeat,
    TaskStatus,
    TaskCompleted,
    TaskFailed,
    TaskStarted,
    TaskProgress,
    NewMotion,
    RateLimitReport,
    // Coordinator → Agent
    Welcome,
    SpeechAdded,
    VoteConfirmed,
    TaskAssigned,
    HeartbeatAck,
    Error,
    DevilsAdvocateRequest,
    DevilsAdvocateResponse,
    RateLimitWarning,
    RateLimited,
    RateLimitReset,
    TaskBlocked,
    TaskUnblocked,
    TaskRetry,
    GraphComplete,
    GraphAborted,
}

/// Generic WebSocket message envelope.
/// Mirrors the Python SDK's `WSMessage` model.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WSMessage {
    #[serde(rename = "type")]
    pub msg_type: MessageType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub motion_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payload: Option<serde_json::Value>,
}

impl WSMessage {
    /// Create a new WSMessage with the given type and optional payload.
    pub fn new(msg_type: MessageType, payload: Option<serde_json::Value>) -> Self {
        Self {
            msg_type,
            motion_id: None,
            agent_id: None,
            timestamp: Some(chrono::Utc::now().to_rfc3339()),
            payload,
        }
    }
}
