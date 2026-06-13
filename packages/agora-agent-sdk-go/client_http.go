package agorasdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// defaultHTTPClient returns a sensible default HTTP client.
func defaultHTTPClient() *http.Client {
	return &http.Client{Timeout: 30 * time.Second}
}

// httpPost sends a JSON POST and returns the response body.
func (c *Client) httpPost(ctx context.Context, path string, body map[string]any) ([]byte, error) {
	data, _ := json.Marshal(body)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.config.CoordinatorURL+path, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.config.AgentToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.AgentToken)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	return io.ReadAll(resp.Body)
}

// httpGet sends a GET request and returns the response body.
func (c *Client) httpGet(ctx context.Context, path string) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		c.config.CoordinatorURL+path, nil)
	if err != nil {
		return nil, err
	}
	if c.config.AgentToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.AgentToken)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	return io.ReadAll(resp.Body)
}
