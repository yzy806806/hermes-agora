package agorasdk

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestReportTaskStartRequiresConnection(t *testing.T) {
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	err := c.ReportTaskStart("t1")
	if err == nil {
		t.Fatal("expected error when not connected")
	}
	if !strings.Contains(err.Error(), "not connected") {
		t.Errorf("error = %q, want 'not connected'", err.Error())
	}
}

func TestReportTaskStartSendsMessage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, msg, _ := conn.ReadMessage()
		var wsMsg WSMessage
		json.Unmarshal(msg, &wsMsg)
		if wsMsg.Type != TaskStarted {
			t.Errorf("type = %q, want TASK_STARTED", wsMsg.Type)
		}
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := withTimeout()
	defer cancel()
	c.Connect(ctx)
	if err := c.ReportTaskStart("t1"); err != nil {
		t.Fatalf("ReportTaskStart: %v", err)
	}
	c.Disconnect()
}

func TestReportTaskProgressSendsMessage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, msg, _ := conn.ReadMessage()
		var wsMsg WSMessage
		json.Unmarshal(msg, &wsMsg)
		if wsMsg.Type != TaskProgress {
			t.Errorf("type = %q, want TASK_PROGRESS", wsMsg.Type)
		}
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := withTimeout()
	defer cancel()
	c.Connect(ctx)
	if err := c.ReportTaskProgress("t1", 50); err != nil {
		t.Fatalf("ReportTaskProgress: %v", err)
	}
	c.Disconnect()
}

func TestReportTaskCompleteSendsMessage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, msg, _ := conn.ReadMessage()
		var wsMsg WSMessage
		json.Unmarshal(msg, &wsMsg)
		if wsMsg.Type != TaskCompleted {
			t.Errorf("type = %q, want TASK_COMPLETED", wsMsg.Type)
		}
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := withTimeout()
	defer cancel()
	c.Connect(ctx)
	err := c.ReportTaskComplete("t1", []string{"/tmp/out"})
	if err != nil {
		t.Fatalf("ReportTaskComplete: %v", err)
	}
	c.Disconnect()
}

func TestReportTaskFailedSendsMessage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, msg, _ := conn.ReadMessage()
		var wsMsg WSMessage
		json.Unmarshal(msg, &wsMsg)
		if wsMsg.Type != TaskFailed {
			t.Errorf("type = %q, want TASK_FAILED", wsMsg.Type)
		}
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := withTimeout()
	defer cancel()
	c.Connect(ctx)
	if err := c.ReportTaskFailed("t1", "oom"); err != nil {
		t.Fatalf("ReportTaskFailed: %v", err)
	}
	c.Disconnect()
}

func TestReportTaskFailedNotConnected(t *testing.T) {
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	err := c.ReportTaskFailed("t1", "fail")
	if err == nil {
		t.Fatal("expected error when not connected")
	}
}

func withTimeout() (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), 3*time.Second)
}
