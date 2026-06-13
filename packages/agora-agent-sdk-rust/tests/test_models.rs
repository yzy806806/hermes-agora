//! Integration tests — data models (AgentConfig, result types, session).

use agora_agent_sdk::{
    AgentConfig, AgentWelcomeConfig, MotionResult, RegistrationResult,
    SpeechResult, TaskNode, VoteResult, SessionFilter, SessionRecord,
};
use std::time::Duration;

#[test]
fn agent_config_new_defaults() {
    let cfg = AgentConfig::new("ws://localhost:8000", "test-agent");
    assert_eq!(cfg.coordinator_url, "ws://localhost:8000");
    assert_eq!(cfg.agent_name, "test-agent");
    assert_eq!(cfg.agent_type, "custom");
    assert!(cfg.capabilities.is_empty());
    assert!(cfg.model.is_empty());
    assert!(cfg.agent_token.is_none());
    assert_eq!(cfg.heartbeat_interval, Duration::from_secs(30));
    assert_eq!(cfg.max_retries, 3);
}

#[test]
fn agent_config_builder_chain() {
    let cfg = AgentConfig::new("ws://localhost:8000", "bot")
        .with_agent_type("hermes")
        .with_capabilities(vec!["code-review".into()])
        .with_model("gpt-4")
        .with_token("secret");
    assert_eq!(cfg.agent_type, "hermes");
    assert_eq!(cfg.capabilities, vec!["code-review"]);
    assert_eq!(cfg.model, "gpt-4");
    assert_eq!(cfg.agent_token.as_deref(), Some("secret"));
}

#[test]
fn registration_result_serde() {
    let json = r#"{"agent_id":"a1","token":"t1","agent_token":"at1"}"#;
    let r: RegistrationResult = serde_json::from_str(json).unwrap();
    assert_eq!(r.agent_id, "a1");
    assert_eq!(r.status, "ok");
    assert_eq!(r.token, "t1");
}

#[test]
fn motion_result_serde() {
    let json = r#"{"motion_id":"m1","status":"ok","message":"created"}"#;
    let r: MotionResult = serde_json::from_str(json).unwrap();
    assert_eq!(r.motion_id, "m1");
    assert_eq!(r.status, "ok");
}

#[test]
fn speech_result_defaults() {
    let json = r#"{}"#;
    let r: SpeechResult = serde_json::from_str(json).unwrap();
    assert!(r.success);
}

#[test]
fn vote_result_serde() {
    let json = r#"{"success":true,"confirmed":true,"message":"voted"}"#;
    let r: VoteResult = serde_json::from_str(json).unwrap();
    assert!(r.success && r.confirmed);
}

#[test]
fn task_node_serde() {
    let json = r#"{"task_id":"t1","title":"fix bug","priority":2}"#;
    let t: TaskNode = serde_json::from_str(json).unwrap();
    assert_eq!(t.id, "t1");
    assert_eq!(t.title, "fix bug");
    assert_eq!(t.priority, 2);
    assert!(t.parent_id.is_none());
}

#[test]
fn welcome_config_defaults() {
    let json = r#"{"agent_id":"a1"}"#;
    let c: AgentWelcomeConfig = serde_json::from_str(json).unwrap();
    assert_eq!(c.agent_type, "custom");
    assert_eq!(c.max_concurrent_tasks, 2);
    assert_eq!(c.heartbeat_interval_seconds, 30);
    assert_eq!(c.tpm_limit, 10000);
}

#[test]
fn session_filter_defaults() {
    let f = SessionFilter::default();
    assert_eq!(f.limit, 20);
    assert!(f.agent_id.is_none());
}

#[test]
fn session_record_serde() {
    let json = r#"{"agent_id":"a1","started_at":"2026-01-01T00:00:00Z"}"#;
    let r: SessionRecord = serde_json::from_str(json).unwrap();
    assert_eq!(r.agent_id, "a1");
    assert_eq!(r.session_type, "task_execution");
    assert_eq!(r.outcome, "success");
}
