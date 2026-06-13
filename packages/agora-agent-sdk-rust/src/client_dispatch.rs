//! Client message dispatch — routes incoming WS text to handler callbacks.

use crate::client::AgoraClient;
use crate::error::AgoraError;
use crate::models_results::TaskNode;
use crate::protocol::*;
use crate::EventHandler;
use log::info;

impl AgoraClient {
    /// Dispatch a text message to the appropriate handler callback.
    pub async fn handle_text<H: EventHandler>(&self, text: &str, handler: &H) {
        if let Ok(msg) = serde_json::from_str::<WSMessage>(text) {
            match msg.msg_type {
                MessageType::TaskAssigned => {
                    if let Some(p) = msg.payload {
                        if let Ok(task) = serde_json::from_value::<TaskNode>(p) {
                            handler.on_task_assigned(task).await;
                        }
                    }
                }
                MessageType::SpeechAdded => {
                    let mid = msg.motion_id.as_deref().unwrap_or("");
                    let content = msg
                        .payload
                        .as_ref()
                        .and_then(|p| p.get("content"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    handler.on_discussion_message(mid, content).await;
                }
                MessageType::Error => {
                    let desc = msg
                        .payload
                        .as_ref()
                        .and_then(|p| p.get("message"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown error");
                    handler.on_error(AgoraError::Protocol(desc.into())).await;
                }
                _ => info!("Unhandled message type: {:?}", msg.msg_type),
            }
        }
    }
}
