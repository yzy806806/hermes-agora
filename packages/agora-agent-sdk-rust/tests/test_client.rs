//! Integration tests — client construction, http_base, and error types.

use agora_agent_sdk::{AgoraClient, AgoraError, AgentConfig};

#[test]
fn client_new_with_valid_config() {
    let cfg = AgentConfig::new("ws://localhost:8000", "agent1");
    let _client = AgoraClient::new(cfg);
    // Client constructed without panic — basic smoke test
}

#[test]
fn http_base_converts_ws_to_http() {
    let cfg = AgentConfig::new("ws://localhost:8000", "agent1");
    let client = AgoraClient::new(cfg);
    assert_eq!(client.http_base(), "http://localhost:8000");
}

#[test]
fn http_base_converts_wss_to_https() {
    let cfg = AgentConfig::new("wss://agora.example.com", "agent1");
    let client = AgoraClient::new(cfg);
    assert_eq!(client.http_base(), "https://agora.example.com");
}

#[test]
fn error_display_messages() {
    assert_eq!(
        AgoraError::ConnectionFailed("refused".into()).to_string(),
        "connection failed: refused"
    );
    assert_eq!(
        AgoraError::NotConnected.to_string(),
        "not connected — call connect() first"
    );
    assert_eq!(
        AgoraError::Protocol("bad msg".into()).to_string(),
        "protocol error: bad msg"
    );
    assert_eq!(
        AgoraError::TaskFailed("timeout".into()).to_string(),
        "task failed: timeout"
    );
}

#[test]
fn config_unique_agent_ids() {
    let c1 = AgentConfig::new("ws://localhost:8000", "a");
    let c2 = AgentConfig::new("ws://localhost:8000", "a");
    assert_ne!(c1.agent_id, c2.agent_id);
}

#[test]
fn config_preserves_url() {
    let cfg = AgentConfig::new("ws://host:9999", "x");
    assert_eq!(cfg.coordinator_url, "ws://host:9999");
}
