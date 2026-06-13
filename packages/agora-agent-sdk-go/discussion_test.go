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

func TestCreateMotion(t *testing.T) {
	want := MotionResult{MotionID: "m1", Status: "open", Message: "created"}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %s, want POST", r.Method)
		}
		if r.URL.Path != "/api/v1/motions" {
			t.Errorf("path = %s, want /api/v1/motions", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(want)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "a1"})
	result, err := c.CreateMotion(context.Background(), "Title", "Desc")
	if err != nil {
		t.Fatalf("CreateMotion: %v", err)
	}
	if result.MotionID != "m1" {
		t.Errorf("MotionID = %q, want m1", result.MotionID)
	}
}

func TestCreateMotionServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Second,
	})
	_, err := c.CreateMotion(context.Background(), "T", "D")
	if err == nil {
		t.Fatal("expected error for 500")
	}
}

func TestSpeakRequiresConnection(t *testing.T) {
	c := NewClient(AgentConfig{
		CoordinatorURL: "http://localhost", AgentID: "a1",
	})
	_, err := c.Speak(context.Background(), "m1", "hello")
	if err == nil {
		t.Fatal("expected error when not connected")
	}
	if !strings.Contains(err.Error(), "not connected") {
		t.Errorf("error = %q, want 'not connected'", err.Error())
	}
}

func TestVoteRequiresConnection(t *testing.T) {
	c := NewClient(AgentConfig{CoordinatorURL: "http://localhost", AgentID: "a1"})
	_, err := c.Vote(context.Background(), "m1", "yes")
	if err == nil {
		t.Fatal("expected error when not connected")
	}
}

func TestSpeakSendsWSMessage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, msg, _ := conn.ReadMessage()
		var wsMsg WSMessage
		json.Unmarshal(msg, &wsMsg)
		if wsMsg.Type != Speak {
			t.Errorf("type = %q, want SPEAK", wsMsg.Type)
		}
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	c.Connect(ctx)
	_, err := c.Speak(ctx, "m1", "hello")
	if err != nil {
		t.Fatalf("Speak: %v", err)
	}
	c.Disconnect()
}

func TestVoteSendsWSMessage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		_, msg, _ := conn.ReadMessage()
		var wsMsg WSMessage
		json.Unmarshal(msg, &wsMsg)
		if wsMsg.Type != Vote {
			t.Errorf("type = %q, want VOTE", wsMsg.Type)
		}
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	c.Connect(ctx)
	_, err := c.Vote(ctx, "m1", "yes")
	if err != nil {
		t.Fatalf("Vote: %v", err)
	}
	c.Disconnect()
}
