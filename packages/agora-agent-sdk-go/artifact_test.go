package agorasdk

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGetArtifact(t *testing.T) {
	content := []byte("artifact-data")
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/projects/p1/artifacts/k1" {
			t.Errorf("path = %q, want /api/v1/projects/p1/artifacts/k1", r.URL.Path)
		}
		if r.Method != http.MethodGet {
			t.Errorf("method = %s, want GET", r.Method)
		}
		w.Write(content)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "x"})
	data, err := c.GetArtifact(context.Background(), "p1", "k1")
	if err != nil {
		t.Fatalf("GetArtifact: %v", err)
	}
	if string(data) != "artifact-data" {
		t.Errorf("data = %q, want artifact-data", string(data))
	}
}

func TestPutArtifact(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			t.Errorf("method = %s, want PUT", r.Method)
		}
		if r.URL.Path != "/api/v1/projects/p1/artifacts/k1" {
			t.Errorf("path = %q", r.URL.Path)
		}
		if r.Header.Get("Content-Type") != "application/octet-stream" {
			t.Errorf("Content-Type = %q", r.Header.Get("Content-Type"))
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "x"})
	if err := c.PutArtifact(context.Background(), "p1", "k1", []byte("val")); err != nil {
		t.Fatalf("PutArtifact: %v", err)
	}
}

func TestListArtifacts(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/projects/p1/artifacts" {
			t.Errorf("path = %q", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{
			"keys": []string{"a", "b"},
		})
	}))
	defer srv.Close()

	c := NewClient(AgentConfig{CoordinatorURL: srv.URL, AgentID: "x"})
	keys, err := c.ListArtifacts(context.Background(), "p1")
	if err != nil {
		t.Fatalf("ListArtifacts: %v", err)
	}
	if len(keys) != 2 || keys[0] != "a" {
		t.Errorf("keys = %v, want [a b]", keys)
	}
}
