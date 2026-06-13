package agorasdk

import (
	"encoding/json"
	"testing"
)

func TestMessageTypeConstants(t *testing.T) {
	// Verify a subset of agent→coordinator message types
	check := map[MessageType]string{
		Register: "REGISTER", Speak: "SPEAK",
		Heartbeat: "HEARTBEAT", Vote: "VOTE",
	}
	for mt, expected := range check {
		if string(mt) != expected {
			t.Errorf("MessageType %v = %q, want %q", mt, string(mt), expected)
		}
	}
	// Verify a subset of coordinator→agent message types
	check2 := map[MessageType]string{
		Welcome: "WELCOME", TaskAssigned: "TASK_ASSIGNED",
		Error: "ERROR", HeartbeatAck: "HEARTBEAT_ACK",
	}
	for mt, expected := range check2 {
		if string(mt) != expected {
			t.Errorf("MessageType %v = %q, want %q", mt, string(mt), expected)
		}
	}
}

func TestWSMessageMarshalUnmarshal(t *testing.T) {
	agentID := "agent-1"
	m := NewWSMessage(Speak, map[string]any{
		"motion_id": "m1", "content": "hello",
	})
	m.AgentID = &agentID
	data, err := json.Marshal(m)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var got WSMessage
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.Type != Speak {
		t.Errorf("Type = %q, want %q", got.Type, Speak)
	}
	if got.AgentID == nil || *got.AgentID != "agent-1" {
		t.Error("AgentID not preserved")
	}
	if got.Timestamp.IsZero() {
		t.Error("Timestamp is zero")
	}
	// Verify payload round-trips
	var payload map[string]string
	if err := json.Unmarshal(got.Payload, &payload); err != nil {
		t.Fatalf("payload unmarshal: %v", err)
	}
	if payload["content"] != "hello" {
		t.Errorf("payload content = %q, want hello", payload["content"])
	}
}

func TestNewWSMessageNilPayload(t *testing.T) {
	m := NewWSMessage(Heartbeat, nil)
	if m.Payload != nil {
		t.Errorf("Payload should be nil for nil input, got %s", m.Payload)
	}
}

func TestNewWSMessageWithPayload(t *testing.T) {
	m := NewWSMessage(TaskStarted, map[string]any{"task_id": "t1"})
	if m.Type != TaskStarted {
		t.Errorf("Type = %q, want %q", m.Type, TaskStarted)
	}
	if len(m.Payload) == 0 {
		t.Error("Payload should not be empty")
	}
}
