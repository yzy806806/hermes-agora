//! Integration tests — EventHandler trait dispatch via handle_text.

use agora_agent_sdk::{
    AgoraClient, AgoraError, AgentConfig, EventHandler, TaskNode,
};
use async_trait::async_trait;
use std::sync::{Arc, Mutex};

/// Record events dispatched to the test handler.
#[derive(Clone, Default)]
struct EventLog {
    tasks: Vec<TaskNode>,
    discussions: Vec<(String, String)>,
    errors: Vec<AgoraError>,
}

struct MockHandler {
    log: Arc<Mutex<EventLog>>,
}

impl MockHandler {
    fn new(log: Arc<Mutex<EventLog>>) -> Self {
        Self { log }
    }
}

#[async_trait]
impl EventHandler for MockHandler {
    async fn on_task_assigned(&self, task: TaskNode) {
        self.log.lock().unwrap().tasks.push(task);
    }
    async fn on_discussion_message(&self, motion_id: &str, content: &str) {
        self.log.lock().unwrap()
            .discussions
            .push((motion_id.into(), content.into()));
    }
    async fn on_error(&self, error: AgoraError) {
        self.log.lock().unwrap().errors.push(error);
    }
}

fn make_client() -> AgoraClient {
    let cfg = AgentConfig::new("ws://localhost:9999", "test-handler");
    AgoraClient::new(cfg)
}

#[tokio::test]
async fn dispatch_task_assigned() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    let handler = MockHandler::new(log.clone());
    let client = make_client();
    let msg = r#"{"type":"TASK_ASSIGNED","payload":{"task_id":"t1","title":"fix"}}"#;
    client.handle_text(msg, &handler).await;
    let l = log.lock().unwrap();
    assert_eq!(l.tasks.len(), 1);
    assert_eq!(l.tasks[0].id, "t1");
}

#[tokio::test]
async fn dispatch_speech_added() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    let handler = MockHandler::new(log.clone());
    let client = make_client();
    let msg = r#"{"type":"SPEECH_ADDED","motion_id":"m1","payload":{"content":"hi"}}"#;
    client.handle_text(msg, &handler).await;
    let l = log.lock().unwrap();
    assert_eq!(l.discussions.len(), 1);
    assert_eq!(l.discussions[0].0, "m1");
    assert_eq!(l.discussions[0].1, "hi");
}

#[tokio::test]
async fn dispatch_error() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    let handler = MockHandler::new(log.clone());
    let client = make_client();
    let msg = r#"{"type":"ERROR","payload":{"message":"boom"}}"#;
    client.handle_text(msg, &handler).await;
    let l = log.lock().unwrap();
    assert_eq!(l.errors.len(), 1);
    match &l.errors[0] {
        AgoraError::Protocol(s) => assert_eq!(s, "boom"),
        other => panic!("expected Protocol error, got {:?}", other),
    }
}

#[tokio::test]
async fn dispatch_unknown_type_ignored() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    let handler = MockHandler::new(log.clone());
    let client = make_client();
    let msg = r#"{"type":"HEARTBEAT_ACK"}"#;
    client.handle_text(msg, &handler).await;
    let l = log.lock().unwrap();
    assert!(l.tasks.is_empty());
    assert!(l.discussions.is_empty());
    assert!(l.errors.is_empty());
}

#[tokio::test]
async fn dispatch_invalid_json_ignored() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    let handler = MockHandler::new(log.clone());
    let client = make_client();
    client.handle_text("not json", &handler).await;
    let l = log.lock().unwrap();
    assert!(l.tasks.is_empty());
}
