//! Error types for the Agora Agent SDK.

use thiserror::Error;

/// All errors produced by the SDK.
#[derive(Error, Debug, Clone)]
pub enum AgoraError {
    #[error("connection failed: {0}")]
    ConnectionFailed(String),

    #[error("registration failed: {0}")]
    RegistrationFailed(String),

    #[error("authentication failed: {0}")]
    AuthFailed(String),

    #[error("not found: {0}")]
    NotFound(String),

    #[error("WebSocket error: {0}")]
    WsError(String),

    #[error("HTTP error: {0}")]
    HttpError(String),

    #[error("serialization error: {0}")]
    SerializationError(String),

    #[error("not connected — call connect() first")]
    NotConnected,

    #[error("task failed: {0}")]
    TaskFailed(String),

    #[error("timeout: {0}")]
    Timeout(String),

    #[error("protocol error: {0}")]
    Protocol(String),

    #[error("config error: {0}")]
    ConfigError(String),
}

impl From<reqwest::Error> for AgoraError {
    fn from(e: reqwest::Error) -> Self {
        AgoraError::HttpError(e.to_string())
    }
}

impl From<serde_json::Error> for AgoraError {
    fn from(e: serde_json::Error) -> Self {
        AgoraError::SerializationError(e.to_string())
    }
}

/// Alias for convenience.
pub type Result<T> = std::result::Result<T, AgoraError>;
