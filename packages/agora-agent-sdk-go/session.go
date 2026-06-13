package agorasdk

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// SessionRecord represents a single agent session stored in Agora DB.
type SessionRecord struct {
	ID             string         `json:"id"`
	AgentID        string         `json:"agent_id"`
	ProjectID      string         `json:"project_id"`
	SessionType    string         `json:"session_type"`
	StartedAt      time.Time      `json:"started_at"`
	EndedAt        *time.Time     `json:"ended_at,omitempty"`
	InputMessages  []map[string]any `json:"input_messages"`
	OutputMessages []map[string]any `json:"output_messages"`
	ToolCalls      []map[string]any `json:"tool_calls"`
	Errors         []map[string]any `json:"errors"`
	Outcome        string         `json:"outcome"`
	Metadata       map[string]any `json:"metadata"`
}

// SessionFilter holds query parameters for searching sessions.
type SessionFilter struct {
	AgentID     string `json:"agent_id,omitempty"`
	ProjectID   string `json:"project_id,omitempty"`
	SessionType string `json:"session_type,omitempty"`
	Outcome     string `json:"outcome,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
}

// QuerySessions queries sessions from the Coordinator REST API.
func (c *Client) QuerySessions(ctx context.Context, filter SessionFilter) ([]SessionRecord, error) {
	path := "/api/v1/sessions?limit=20"
	if filter.AgentID != "" {
		path += "&agent_id=" + filter.AgentID
	}
	if filter.ProjectID != "" {
		path += "&project_id=" + filter.ProjectID
	}
	if filter.SessionType != "" {
		path += "&session_type=" + filter.SessionType
	}
	data, err := c.httpGet(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("query_sessions: %w", err)
	}
	var result struct {
		Sessions []SessionRecord `json:"sessions"`
	}
	if err := json.Unmarshal(data, &result); err != nil {
		// Try direct array
		var sessions []SessionRecord
		if err2 := json.Unmarshal(data, &sessions); err2 != nil {
			return nil, fmt.Errorf("query_sessions: decode: %w", err)
		}
		return sessions, nil
	}
	return result.Sessions, nil
}
