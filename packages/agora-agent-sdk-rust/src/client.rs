//! AgoraClient — the main SDK entry point.

use crate::error::{AgoraError, Result};
use crate::models::AgentConfig;
use crate::models_results::RegistrationResult;
use futures_util::StreamExt;
use log::info;
use reqwest::Client as HttpClient;
use tokio_tungstenite::{connect_async, tungstenite::Message};

/// Main client for communicating with the Agora Coordinator.
pub struct AgoraClient {
    pub(crate) config: AgentConfig,
    pub(crate) http: HttpClient,
    pub(crate) ws_tx: Option<
        futures_util::stream::SplitSink<
            tokio_tungstenite::WebSocketStream<
                tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
            >,
            Message,
        >,
    >,
    pub(crate) ws_rx: Option<
        futures_util::stream::SplitStream<
            tokio_tungstenite::WebSocketStream<
                tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
            >,
        >,
    >,
}

impl AgoraClient {
    pub fn new(config: AgentConfig) -> Self {
        Self {
            config,
            http: HttpClient::new(),
            ws_tx: None,
            ws_rx: None,
        }
    }

    /// Register this agent with the Coordinator via HTTP.
    pub async fn register(&self) -> Result<RegistrationResult> {
        let url = format!(
            "{}/api/v1/agents",
            self.config
                .coordinator_url
                .replace("ws://", "http://")
                .replace("wss://", "https://")
        );
        let body = serde_json::json!({
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "agent_type": self.config.agent_type,
            "capabilities": self.config.capabilities,
            "model": self.config.model,
        });
        let resp = self.http.post(&url).json(&body).send().await?;
        let result: RegistrationResult = resp.json().await?;
        info!("Registered as agent {}", result.agent_id);
        Ok(result)
    }

    /// Open a WebSocket connection to the Coordinator.
    pub async fn connect(&mut self) -> Result<()> {
        let ws_url = format!(
            "{}/ws/agents?agent_id={}",
            self.config.coordinator_url, self.config.agent_id
        );
        let (ws_stream, _) = connect_async(&ws_url)
            .await
            .map_err(|e| AgoraError::ConnectionFailed(e.to_string()))?;
        let (tx, rx) = ws_stream.split();
        self.ws_tx = Some(tx);
        self.ws_rx = Some(rx);
        info!("WebSocket connected to {}", ws_url);
        Ok(())
    }
}
