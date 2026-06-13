package agorasdk

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

func TestConnectSuccess(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		// Read one message (the heartbeat) then close
		conn.ReadMessage()
	}))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	_ = wsURL
	c := NewClient(AgentConfig{
		CoordinatorURL: "http" + strings.TrimPrefix(srv.URL, "http"),
		AgentID: "a1", HeartbeatInterval: time.Hour,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := c.Connect(ctx); err != nil {
		t.Fatalf("Connect: %v", err)
	}
	if !c.connected {
		t.Error("expected connected=true")
	}
	c.Disconnect()
}

func TestConnectRefused(t *testing.T) {
	c := NewClient(AgentConfig{
		CoordinatorURL: "http://127.0.0.1:1",
		AgentID: "a1", HeartbeatInterval: time.Hour,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	err := c.Connect(ctx)
	if err == nil {
		t.Fatal("expected error for refused connection")
		c.Disconnect()
	}
}

func TestDisconnectSetsDisconnected(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, _ := upgrader.Upgrade(w, r, nil)
		defer conn.Close()
		time.Sleep(5 * time.Second)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{
		CoordinatorURL: srv.URL, AgentID: "a1",
		HeartbeatInterval: time.Hour,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	c.Connect(ctx)
	c.Disconnect()
	if c.connected {
		t.Error("expected connected=false after Disconnect")
	}
}

func TestWSURLConstruction(t *testing.T) {
	c := NewClient(AgentConfig{
		CoordinatorURL: "http://host:8000",
		AgentID: "a1",
	})
	got := c.wsURL()
	want := "ws://host:8000/ws/a1"
	if got != want {
		t.Errorf("wsURL = %q, want %q", got, want)
	}
}

func TestWSURLWithToken(t *testing.T) {
	c := NewClient(AgentConfig{
		CoordinatorURL: "http://host:8000",
		AgentID: "a1", AgentToken: "secret",
	})
	got := c.wsURL()
	if !strings.Contains(got, "token=secret") {
		t.Errorf("wsURL should contain token, got %q", got)
	}
}
