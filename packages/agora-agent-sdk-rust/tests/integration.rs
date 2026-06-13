//! Integration tests — client registration with mock HTTP server.

use agora_agent_sdk::{AgoraClient, AgentConfig};
use wiremock::{Mock, MockServer, ResponseTemplate};
use wiremock::matchers::{method, path};

#[tokio::test]
async fn register_with_mock_server() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/api/v1/agents"))
        .respond_with(ResponseTemplate::new(200).set_body_json(
            serde_json::json!({"agent_id":"a1","token":"t1","status":"ok","agent_token":"at1"}),
        ))
        .mount(&server)
        .await;
    let url = format!("http://{}", server.address());
    let cfg = AgentConfig::new(&url, "test-agent");
    let client = AgoraClient::new(cfg);
    let result = client.register().await.unwrap();
    assert_eq!(result.agent_id, "a1");
    assert_eq!(result.status, "ok");
}

#[tokio::test]
async fn register_returns_token() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/api/v1/agents"))
        .respond_with(ResponseTemplate::new(200).set_body_json(
            serde_json::json!({"agent_id":"a2","token":"tk","agent_token":"at2"}),
        ))
        .mount(&server)
        .await;
    let url = format!("http://{}", server.address());
    let client = AgoraClient::new(AgentConfig::new(&url, "bot"));
    let result = client.register().await.unwrap();
    assert_eq!(result.token, "tk");
    assert_eq!(result.agent_token, "at2");
}
