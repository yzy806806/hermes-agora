package agorasdk

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestRegisterSuccess(t *testing.T) {
	want := RegistrationResult{
		AgentID: "a1", Token: "tok", Status: "ok",
		Message: "registered", AgentToken: "at-123",
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %s, want POST", r.Method)
		}
		if r.URL.Path != "/api/v1/agents/register" {
			t.Errorf("path = %s, want /api/v1/agents/register", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(want)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		AgentName: "test", AgentType: "custom",
		Capabilities: []string{"code"}, Model: "gpt-4",
	})
	result, err := c.Register(context.Background())
	if err != nil {
		t.Fatalf("Register: %v", err)
	}
	if result.AgentID != "a1" {
		t.Errorf("AgentID = %q, want a1", result.AgentID)
	}
	if result.AgentToken != "at-123" {
		t.Errorf("AgentToken = %q, want at-123", result.AgentToken)
	}
}

func TestRegisterServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		AgentName: "test", AgentType: "custom",
		HeartbeatInterval: time.Second,
	})
	_, err := c.Register(context.Background())
	if err == nil {
		t.Fatal("expected error for 500 response")
	}
}

func TestRegisterSetsAgentToken(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(RegistrationResult{AgentToken: "saved-token"})
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "x"})
	_, _ = c.Register(context.Background())
	if c.config.AgentToken != "saved-token" {
		t.Errorf("AgentToken = %q, want saved-token", c.config.AgentToken)
	}
}

func TestNewClientDefaults(t *testing.T) {
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost:8000"})
	if c.config.HeartbeatInterval != 30*time.Second {
		t.Errorf("default HeartbeatInterval = %v, want 30s", c.config.HeartbeatInterval)
	}
	if c.config.MaxRetries != 3 {
		t.Errorf("default MaxRetries = %d, want 3", c.config.MaxRetries)
	}
}
