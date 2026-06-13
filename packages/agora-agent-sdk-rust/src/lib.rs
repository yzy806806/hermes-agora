//! Agora Agent SDK for Rust — connect any Rust agent to Agora Coordinator.
//!
//! See [`AgoraClient`] for the main entry point and [`EventHandler`]
//! for the callback trait you implement to handle incoming messages.

mod client;
mod client_discussion;
mod client_dispatch;
mod client_run;
mod client_session;
mod client_task;
mod error;
mod models;
mod models_results;
mod protocol;
mod session;

pub use client::AgoraClient;
pub use error::AgoraError;
pub use models::{AgentConfig, AgentWelcomeConfig};
pub use models_results::{MotionResult, RegistrationResult, SpeechResult, TaskNode, VoteResult};
pub use protocol::{MessageType, WSMessage};
pub use session::{SessionFilter, SessionNote, SessionRecord};

use async_trait::async_trait;

/// Callback trait for handling events from the Agora Coordinator.
///
/// Implement this trait and pass an instance to [`AgoraClient::run`].
#[async_trait]
pub trait EventHandler: Send + Sync {
    /// Called when the Coordinator assigns a task to this agent.
    async fn on_task_assigned(&self, task: TaskNode);

    /// Called when a new discussion message arrives for a motion.
    async fn on_discussion_message(&self, motion_id: &str, content: &str);

    /// Called when a protocol or connection error occurs.
    async fn on_error(&self, error: AgoraError);
}

pub const SDK_VERSION: &str = env!("CARGO_PKG_VERSION");
