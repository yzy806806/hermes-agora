//! Integration tests — protocol model serialization/deserialization.

use agora_agent_sdk::{MessageType, WSMessage};

#[test]
fn all_message_types_roundtrip() {
    let variants = vec![
        MessageType::Register, MessageType::Deregister,
        MessageType::Speak, MessageType::RequestSpeak,
        MessageType::Vote, MessageType::Heartbeat,
        MessageType::TaskStatus, MessageType::TaskCompleted,
        MessageType::TaskFailed, MessageType::TaskStarted,
        MessageType::TaskProgress, MessageType::NewMotion,
        MessageType::Welcome, MessageType::SpeechAdded,
        MessageType::VoteConfirmed, MessageType::TaskAssigned,
        MessageType::HeartbeatAck, MessageType::Error,
        MessageType::DevilsAdvocateRequest,
        MessageType::RateLimitWarning, MessageType::RateLimited,
        MessageType::RateLimitReset, MessageType::TaskBlocked,
        MessageType::TaskUnblocked, MessageType::TaskRetry,
        MessageType::GraphComplete, MessageType::GraphAborted,
    ];
    for v in variants {
        let json = serde_json::to_string(&v).unwrap();
        let back: MessageType = serde_json::from_str(&json).unwrap();
        assert_eq!(v, back, "roundtrip failed for {:?}", v);
    }
}

#[test]
fn ws_message_with_payload_roundtrip() {
    let msg = WSMessage::new(
        MessageType::TaskAssigned,
        Some(serde_json::json!({"task_id":"t1","title":"fix bug"})),
    );
    let json = serde_json::to_string(&msg).unwrap();
    let back: WSMessage = serde_json::from_str(&json).unwrap();
    assert_eq!(back.msg_type, MessageType::TaskAssigned);
    assert_eq!(back.payload.unwrap()["task_id"], "t1");
}

#[test]
fn ws_message_screaming_snake_case() {
    let json = serde_json::to_string(&MessageType::TaskAssigned).unwrap();
    assert_eq!(json, "\"TASK_ASSIGNED\"");
    let parsed: MessageType = serde_json::from_str("\"TASK_ASSIGNED\"").unwrap();
    assert_eq!(parsed, MessageType::TaskAssigned);
}

#[test]
fn ws_message_skips_none_fields() {
    let msg = WSMessage::new(MessageType::Heartbeat, None);
    let json = serde_json::to_string(&msg).unwrap();
    assert!(!json.contains("motion_id"));
    assert!(!json.contains("agent_id"));
    assert!(!json.contains("payload"));
}
