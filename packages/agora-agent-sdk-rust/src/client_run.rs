//! Client run loop — main event dispatch + heartbeat.

use crate::client::AgoraClient;
use crate::error::{AgoraError, Result};
use crate::protocol::*;
use crate::EventHandler;
use futures_util::{SinkExt, StreamExt};
use log::warn;
use tokio_tungstenite::tungstenite::Message;

impl AgoraClient {
    /// Enter the main event loop — dispatches incoming WS messages to handler.
    pub async fn run<H: EventHandler>(&mut self, handler: H) -> Result<()> {
        let rx = self.ws_rx.take().ok_or(AgoraError::NotConnected)?;
        let mut tx = self.ws_tx.take().ok_or(AgoraError::NotConnected)?;
        let mut interval = tokio::time::interval(self.config.heartbeat_interval);
        let mut rx = rx;

        loop {
            tokio::select! {
                msg = rx.next() => {
                    match msg {
                        Some(Ok(Message::Text(text))) => {
                            self.handle_text(&text, &handler).await;
                        }
                        Some(Ok(Message::Close(_))) | None => {
                            warn!("WebSocket closed");
                            break;
                        }
                        Some(Ok(Message::Ping(data))) => {
                            let _ = tx.send(Message::Pong(data)).await;
                        }
                        _ => {}
                    }
                }
                _ = interval.tick() => {
                    let hb = WSMessage::new(
                        MessageType::Heartbeat, None,
                    );
                    let json = serde_json::to_string(&hb)?;
                    tx.send(Message::Text(json)).await
                        .map_err(|e| AgoraError::WsError(e.to_string()))?;
                }
            }
        }
        self.ws_tx = Some(tx);
        self.ws_rx = Some(rx);
        Ok(())
    }
}
