//! Client disconnect + task reporting methods.

use crate::client::AgoraClient;
use crate::error::{AgoraError, Result};
use futures_util::SinkExt;
use log::info;
use tokio_tungstenite::tungstenite::Message;

impl AgoraClient {
    /// Close the WebSocket connection.
    pub async fn disconnect(&mut self) -> Result<()> {
        if let Some(mut tx) = self.ws_tx.take() {
            tx.send(Message::Close(None))
                .await
                .map_err(|e| AgoraError::WsError(e.to_string()))?;
        }
        self.ws_rx.take();
        info!("Disconnected");
        Ok(())
    }

    /// Report task started via HTTP.
    pub async fn report_task_start(&self, task_id: &str) -> Result<()> {
        let url = self.task_url(task_id);
        let body = serde_json::json!({"status": "in_progress"});
        self.http.put(&url).json(&body).send().await?;
        Ok(())
    }

    /// Report task completed via HTTP.
    pub async fn report_task_complete(&self, task_id: &str, artifacts: Vec<String>) -> Result<()> {
        let url = self.task_url(task_id);
        let body = serde_json::json!({"status": "completed", "artifacts": artifacts});
        self.http.put(&url).json(&body).send().await?;
        Ok(())
    }

    /// Report task failed via HTTP.
    pub async fn report_task_failed(&self, task_id: &str, error: &str) -> Result<()> {
        let url = self.task_url(task_id);
        let body = serde_json::json!({"status": "failed", "error": error});
        self.http.put(&url).json(&body).send().await?;
        Ok(())
    }

    fn task_url(&self, task_id: &str) -> String {
        let base = self
            .config
            .coordinator_url
            .replace("ws://", "http://")
            .replace("wss://", "https://");
        format!("{}/api/v1/tasks/{}", base, task_id)
    }
}
