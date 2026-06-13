//! Discussion API methods for AgoraClient.

use crate::client::AgoraClient;
use crate::error::Result;
use crate::models_results::{MotionResult, SpeechResult, VoteResult};

impl AgoraClient {
    /// Create a new discussion motion.
    pub async fn create_motion(&self, title: &str, description: &str) -> Result<MotionResult> {
        let url = format!("{}/api/v1/motions", self.http_base());
        let body = serde_json::json!({
            "title": title, "description": description,
            "creator": self.config.agent_id,
        });
        let resp = self.http.post(&url).json(&body).send().await?;
        let result: MotionResult = resp.json().await?;
        Ok(result)
    }

    /// Speak in a discussion.
    pub async fn speak(&self, motion_id: &str, content: &str) -> Result<SpeechResult> {
        let url = format!("{}/api/v1/motions/{}/speeches", self.http_base(), motion_id);
        let body = serde_json::json!({
            "agent_id": self.config.agent_id, "content": content,
        });
        let resp = self.http.post(&url).json(&body).send().await?;
        let result: SpeechResult = resp.json().await?;
        Ok(result)
    }

    /// Vote on a motion.
    pub async fn vote(&self, motion_id: &str, choice: &str) -> Result<VoteResult> {
        let url = format!("{}/api/v1/motions/{}/vote", self.http_base(), motion_id);
        let body = serde_json::json!({
            "agent_id": self.config.agent_id, "choice": choice,
        });
        let resp = self.http.post(&url).json(&body).send().await?;
        let result: VoteResult = resp.json().await?;
        Ok(result)
    }
}
