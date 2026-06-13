//! Integration tests — session/artifact API calls with mock HTTP server.

use agora_agent_sdk::{AgoraClient, AgentConfig, SessionFilter};
use wiremock::{Mock, MockServer, ResponseTemplate};
use wiremock::matchers::{method, path};

#[tokio::test]
async fn query_sessions_with_mock() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/api/v1/sessions"))
        .respond_with(ResponseTemplate::new(200).set_body_json(
            serde_json::json!([{"agent_id":"a1","started_at":"2026-01-01T00:00:00Z"}]),
        ))
        .mount(&server)
        .await;
    let url = format!("http://{}", server.address());
    let client = AgoraClient::new(AgentConfig::new(&url, "s"));
    let records = client.query_sessions(&SessionFilter::default()).await.unwrap();
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].agent_id, "a1");
}

#[tokio::test]
async fn get_artifact_with_mock() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/api/v1/projects/p1/artifacts/k1"))
        .respond_with(ResponseTemplate::new(200).set_body_string("hello"))
        .mount(&server)
        .await;
    let url = format!("http://{}", server.address());
    let client = AgoraClient::new(AgentConfig::new(&url, "a"));
    let data = client.get_artifact("p1", "k1").await.unwrap();
    assert_eq!(data, b"hello");
}

#[tokio::test]
async fn put_artifact_with_mock() {
    let server = MockServer::start().await;
    Mock::given(method("PUT"))
        .and(path("/api/v1/projects/p1/artifacts/k1"))
        .respond_with(ResponseTemplate::new(204))
        .mount(&server)
        .await;
    let url = format!("http://{}", server.address());
    let client = AgoraClient::new(AgentConfig::new(&url, "a"));
    let result = client.put_artifact("p1", "k1", b"data").await;
    assert!(result.is_ok());
}
