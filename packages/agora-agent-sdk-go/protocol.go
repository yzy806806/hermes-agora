// Package agorasdk provides a Go client for the Agora Coordinator.
package agorasdk

import (
	"encoding/json"
	"time"
)

// MessageType defines WebSocket message types for agent-coordinator
// communication. Values match the Python SDK MessageType enum.
type MessageType string

const (
	// Agent → Coordinator
	Register              MessageType = "REGISTER"
	Deregister            MessageType = "DEREGISTER"
	Speak                 MessageType = "SPEAK"
	RequestSpeak          MessageType = "REQUEST_SPEAK"
	Vote                  MessageType = "VOTE"
	Heartbeat             MessageType = "HEARTBEAT"
	TaskStatus            MessageType = "TASK_STATUS"
	TaskCompleted         MessageType = "TASK_COMPLETED"
	TaskFailed            MessageType = "TASK_FAILED"
	TaskStarted           MessageType = "TASK_STARTED"
	TaskProgress          MessageType = "TASK_PROGRESS"
	NewMotion             MessageType = "NEW_MOTION"
	RateLimitReport       MessageType = "RATE_LIMIT_REPORT"

	// Coordinator → Agent
	Welcome               MessageType = "WELCOME"
	SpeechAdded           MessageType = "SPEECH_ADDED"
	VoteConfirmed         MessageType = "VOTE_CONFIRMED"
	TaskAssigned          MessageType = "TASK_ASSIGNED"
	HeartbeatAck          MessageType = "HEARTBEAT_ACK"
	Error                 MessageType = "ERROR"
	DevilsAdvocateRequest MessageType = "DEVILS_ADVOCATE_REQUEST"
	DevilsAdvocateResponse MessageType = "DEVILS_ADVOCATE_RESPONSE"
	RateLimitWarning      MessageType = "RATE_LIMIT_WARNING"
	RateLimited           MessageType = "RATE_LIMITED"
	RateLimitReset        MessageType = "RATE_LIMIT_RESET"
	TaskBlocked           MessageType = "TASK_BLOCKED"
	TaskUnblocked         MessageType = "TASK_UNBLOCKED"
	TaskRetry             MessageType = "TASK_RETRY"
	GraphComplete         MessageType = "GRAPH_COMPLETE"
	GraphAborted          MessageType = "GRAPH_ABORTED"
)

// WSMessage is the generic WebSocket message envelope.
type WSMessage struct {
	Type      MessageType     `json:"type"`
	MotionID  *string         `json:"motion_id,omitempty"`
	AgentID   *string         `json:"agent_id,omitempty"`
	Timestamp time.Time       `json:"timestamp"`
	Payload   json.RawMessage `json:"payload,omitempty"`
}

// NewWSMessage creates a WSMessage with current UTC timestamp.
// If payload is non-nil, it is marshalled to JSON.
func NewWSMessage(msgType MessageType, payload interface{}) *WSMessage {
	m := &WSMessage{
		Type:      msgType,
		Timestamp: time.Now().UTC(),
	}
	if payload != nil {
		b, err := json.Marshal(payload)
		if err == nil {
			m.Payload = b
		}
	}
	return m
}
