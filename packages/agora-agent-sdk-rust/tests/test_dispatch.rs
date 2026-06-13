//! Integration tests — EventHandler trait dispatch via handle_text.

use agora_agent_sdk::{AgoraClient, AgoraError, AgentConfig, EventHandler, TaskNode};
use async_trait::async_trait;
use std::sync::{Arc, Mutex};

#[derive(Default)]
struct EventLog { tasks: Vec<TaskNode>, discussions: Vec<(String, String)>, errors: Vec<AgoraError> }

struct MockHandler { log: Arc<Mutex<EventLog>> }

#[async_trait]
impl EventHandler for MockHandler {
    async fn on_task_assigned(&self, task: TaskNode) {
        self.log.lock().unwrap().tasks.push(task);
    }
    async fn on_discussion_message(&self, mid: &str, content: &str) {
        self.log.lock().unwrap().discussions.push((mid.into(), content.into()));
    }
    async fn on_error(&self, error: AgoraError) {
        self.log.lock().unwrap().errors.push(error);
    }
}

fn make_client() -> AgoraClient {
    AgoraClient::new(AgentConfig::new("ws://localhost:19999", "it"))
}

#[tokio::test]
async fn dispatch_task_assigned() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    make_client().handle_text(
        r#"{"type":"TASK_ASSIGNED","payload":{"task_id":"t1","title":"fix"}}"#,
        &MockHandler { log: log.clone() },
    ).await;
    assert_eq!(log.lock().unwrap().tasks[0].id, "t1");
}

#[tokio::test]
async fn dispatch_discussion_message() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    make_client().handle_text(
        r#"{"type":"SPEECH_ADDED","motion_id":"m1","payload":{"content":"hi"}}"#,
        &MockHandler { log: log.clone() },
    ).await;
    let l = log.lock().unwrap();
    assert_eq!(l.discussions[0], ("m1".into(), "hi".into()));
}

#[tokio::test]
async fn dispatch_error() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    make_client().handle_text(
        r#"{"type":"ERROR","payload":{"message":"boom"}}"#,
        &MockHandler { log: log.clone() },
    ).await;
    let guard = log.lock().unwrap();
    match &guard.errors[0] {
        AgoraError::Protocol(s) => assert_eq!(s, "boom"),
        e => panic!("expected Protocol, got {:?}", e),
    };
}

#[tokio::test]
async fn dispatch_unknown_ignored() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    make_client().handle_text(
        r#"{"type":"HEARTBEAT_ACK"}"#, &MockHandler { log: log.clone() },
    ).await;
    let l = log.lock().unwrap();
    assert!(l.tasks.is_empty() && l.discussions.is_empty() && l.errors.is_empty());
}

#[tokio::test]
async fn dispatch_invalid_json_ignored() {
    let log = Arc::new(Mutex::new(EventLog::default()));
    make_client().handle_text("not json", &MockHandler { log: log.clone() }).await;
    assert!(log.lock().unwrap().tasks.is_empty());
}
