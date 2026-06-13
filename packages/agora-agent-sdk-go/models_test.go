package agorasdk

import (
	"encoding/json"
	"testing"
	"time"
)

func TestAgentWelcomeConfigDeserialize(t *testing.T) {
	raw := `{
		"agent_id":"a1","name":"test","agent_type":"custom",
		"capabilities":["code","review"],"model":"gpt-4",
		"max_concurrent_tasks":5,"heartbeat_interval_seconds":30,
		"heartbeat_timeout_seconds":90,"tpm_limit":1000,
		"tpm_burst_factor":1.5,"allowed_discussion_roles":["speaker"],
		"auto_accept_tasks":true
	}`
	var cfg AgentWelcomeConfig
	if err := json.Unmarshal([]byte(raw), &cfg); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if cfg.AgentID != "a1" {
		t.Errorf("AgentID = %q, want a1", cfg.AgentID)
	}
	if cfg.MaxConcurrentTasks != 5 {
		t.Errorf("MaxConcurrentTasks = %d, want 5", cfg.MaxConcurrentTasks)
	}
	if !cfg.AutoAcceptTasks {
		t.Error("AutoAcceptTasks should be true")
	}
	if cfg.TPMBurstFactor != 1.5 {
		t.Errorf("TPMBurstFactor = %v, want 1.5", cfg.TPMBurstFactor)
	}
}

func TestTaskNodeDeserialize(t *testing.T) {
	raw := `{
		"task_id":"t1","title":"Fix bug","description":"desc",
		"priority":2,"capabilities":["go"],"artifact_paths":["/tmp/out"],
		"created_at":"2026-01-01T00:00:00Z"
	}`
	var tn TaskNode
	if err := json.Unmarshal([]byte(raw), &tn); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if tn.TaskID != "t1" {
		t.Errorf("TaskID = %q, want t1", tn.TaskID)
	}
	if tn.Priority != 2 {
		t.Errorf("Priority = %d, want 2", tn.Priority)
	}
	if tn.ParentID != nil {
		t.Errorf("ParentID should be nil, got %v", *tn.ParentID)
	}
	if len(tn.ArtifactPaths) != 1 {
		t.Errorf("ArtifactPaths len = %d, want 1", len(tn.ArtifactPaths))
	}
}

func TestSessionRecordRoundTrip(t *testing.T) {
	sr := SessionRecord{
		ID: "s1", AgentID: "a1", Outcome: "success",
		StartedAt: time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC),
	}
	data, err := json.Marshal(sr)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var got SessionRecord
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.ID != "s1" || got.Outcome != "success" {
		t.Errorf("round-trip failed: %+v", got)
	}
}

func TestVoteResultDeserialize(t *testing.T) {
	raw := `{"success":true,"confirmed":true,"message":"vote recorded"}`
	var vr VoteResult
	if err := json.Unmarshal([]byte(raw), &vr); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if !vr.Confirmed {
		t.Error("Confirmed should be true")
	}
}

func TestMotionResultDeserialize(t *testing.T) {
	raw := `{"motion_id":"m1","status":"open","message":"created"}`
	var mr MotionResult
	if err := json.Unmarshal([]byte(raw), &mr); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if mr.MotionID != "m1" {
		t.Errorf("MotionID = %q, want m1", mr.MotionID)
	}
	if mr.Status != "open" {
		t.Errorf("Status = %q, want open", mr.Status)
	}
}

func TestTaskNodeWithParent(t *testing.T) {
	pid := "parent-1"
	tn := TaskNode{TaskID: "t2", ParentID: &pid}
	data, _ := json.Marshal(tn)
	var got TaskNode
	json.Unmarshal(data, &got)
	if got.ParentID == nil || *got.ParentID != "parent-1" {
		t.Error("ParentID not preserved in round-trip")
	}
}
