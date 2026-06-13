package agorasdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

// GetArtifact retrieves a project artifact by key.
func (c *Client) GetArtifact(ctx context.Context, projectID, key string) ([]byte, error) {
	path := fmt.Sprintf(
		"/api/v1/projects/%s/artifacts/%s", projectID, key,
	)
	data, err := c.httpGet(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("get_artifact: %w", err)
	}
	return data, nil
}

// PutArtifact stores a project artifact by key.
func (c *Client) PutArtifact(ctx context.Context, projectID, key string, value []byte) error {
	path := fmt.Sprintf(
		"/api/v1/projects/%s/artifacts/%s", projectID, key,
	)
	req, err := http.NewRequestWithContext(
		ctx, http.MethodPut,
		c.config.CoordinatorURL+path, bytes.NewReader(value),
	)
	if err != nil {
		return fmt.Errorf("put_artifact: %w", err)
	}
	req.Header.Set("Content-Type", "application/octet-stream")
	if c.config.AgentToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.AgentToken)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("put_artifact: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("put_artifact: HTTP %d", resp.StatusCode)
	}
	return nil
}

// ListArtifacts lists artifact keys for a project.
func (c *Client) ListArtifacts(ctx context.Context, projectID string) ([]string, error) {
	path := fmt.Sprintf("/api/v1/projects/%s/artifacts", projectID)
	data, err := c.httpGet(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("list_artifacts: %w", err)
	}
	var result struct {
		Keys []string `json:"keys"`
	}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("list_artifacts: decode: %w", err)
	}
	return result.Keys, nil
}
