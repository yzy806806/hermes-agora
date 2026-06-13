package agorasdk

import (
	"encoding/json"
	"testing"
)

func TestHandleMessageTaskAssigned(t *testing.T) {
	called := false
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	c.OnTaskAssigned = func(raw json.RawMessage) {
		called = true
		var payload map[string]any
		json.Unmarshal(raw, &payload)
		if payload["task_id"] != "t1" {
			t.Errorf("payload task_id = %v, want t1", payload["task_id"])
		}
	}
	msg := NewWSMessage(TaskAssigned, map[string]any{"task_id": "t1"})
	data, _ := json.Marshal(msg)
	c.handleMessage(data)
	if !called {
		t.Error("OnTaskAssigned should have been called")
	}
}

func TestHandleMessageIgnoresOtherTypes(t *testing.T) {
	called := false
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	c.OnTaskAssigned = func(raw json.RawMessage) { called = true }
	msg := NewWSMessage(Welcome, map[string]any{"agent_id": "a1"})
	data, _ := json.Marshal(msg)
	c.handleMessage(data)
	if called {
		t.Error("OnTaskAssigned should NOT be called for WELCOME")
	}
}

func TestHandleMessageInvalidJSON(t *testing.T) {
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	// Should not panic on invalid JSON
	c.handleMessage([]byte("not-json"))
}

func TestHandleMessageNoCallback(t *testing.T) {
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	// OnTaskAssigned is nil — should not panic
	msg := NewWSMessage(TaskAssigned, map[string]any{"task_id": "t1"})
	data, _ := json.Marshal(msg)
	c.handleMessage(data)
}
