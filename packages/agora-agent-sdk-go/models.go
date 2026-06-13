package agorasdk

import "time"

// AgentConfig is the client-side configuration for creating a new Client.
type AgentConfig struct {
	CoordinatorURL    string
	AgentID           string
	AgentName         string
	AgentType         string // "hermes", "cli", "docker", "custom"
	Capabilities      []string
	Model             string
	AgentToken        string
	HeartbeatInterval time.Duration
	MaxRetries        int
}

// AgentWelcomeConfig holds per-agent runtime configuration
// received in the WELCOME message payload from the coordinator.
type AgentWelcomeConfig struct {
	AgentID                  string   `json:"agent_id"`
	Name                     string   `json:"name"`
	AgentType                string   `json:"agent_type"`
	Capabilities             []string `json:"capabilities"`
	Model                    string   `json:"model"`
	MaxConcurrentTasks       int      `json:"max_concurrent_tasks"`
	HeartbeatIntervalSeconds int      `json:"heartbeat_interval_seconds"`
	HeartbeatTimeoutSeconds  int      `json:"heartbeat_timeout_seconds"`
	TPMLimit                 int      `json:"tpm_limit"`
	TPMBurstFactor           float64  `json:"tpm_burst_factor"`
	AllowedDiscussionRoles   []string `json:"allowed_discussion_roles"`
	AutoAcceptTasks          bool     `json:"auto_accept_tasks"`
}

// RegistrationResult is the result of agent registration.
type RegistrationResult struct {
	AgentID    string `json:"agent_id"`
	Token      string `json:"token"`
	Status     string `json:"status"`
	Message    string `json:"message"`
	AgentToken string `json:"agent_token"`
}

// MotionResult is the result of a create_motion call.
type MotionResult struct {
	MotionID string `json:"motion_id"`
	Status   string `json:"status"`
	Message  string `json:"message"`
}

// SpeechResult is the result of a speak call.
type SpeechResult struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// VoteResult is the result of a vote call.
type VoteResult struct {
	Success   bool   `json:"success"`
	Confirmed bool   `json:"confirmed"`
	Message   string `json:"message"`
}

// TaskNode represents a task assignment from the coordinator.
type TaskNode struct {
	TaskID        string    `json:"task_id"`
	Title         string    `json:"title"`
	Description   string    `json:"description"`
	ParentID      *string   `json:"parent_id,omitempty"`
	Priority      int       `json:"priority"`
	Capabilities  []string  `json:"capabilities,omitempty"`
	ArtifactPaths []string  `json:"artifact_paths,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
}
