package agorasdk

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestQuerySessionsWrapped(t *testing.T) {
	records := []SessionRecord{
		{ID: "s1", AgentID: "a1", Outcome: "success"},
		{ID: "s2", AgentID: "a2", Outcome: "failed"},
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Query().Get("agent_id") != "a1" {
			t.Errorf("agent_id param = %q, want a1", r.URL.Query().Get("agent_id"))
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"sessions": records})
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "x"})
	result, err := c.QuerySessions(context.Background(), SessionFilter{AgentID: "a1"})
	if err != nil {
		t.Fatalf("QuerySessions: %v", err)
	}
	if len(result) != 2 {
		t.Fatalf("len = %d, want 2", len(result))
	}
	if result[0].ID != "s1" {
		t.Errorf("result[0].ID = %q, want s1", result[0].ID)
	}
}

func TestQuerySessionsDirectArray(t *testing.T) {
	records := []SessionRecord{{ID: "s3", Outcome: "completed"}}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(records)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "x"})
	result, err := c.QuerySessions(context.Background(), SessionFilter{})
	if err != nil {
		t.Fatalf("QuerySessions: %v", err)
	}
	if len(result) != 1 || result[0].ID != "s3" {
		t.Errorf("unexpected result: %+v", result)
	}
}

func TestQuerySessionsServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "x",
		HeartbeatInterval: time.Second,
	})
	_, err := c.QuerySessions(context.Background(), SessionFilter{})
	if err == nil {
		t.Fatal("expected error for 500")
	}
}
