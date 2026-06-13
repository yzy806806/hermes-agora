package agorasdk

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
)

// Register registers this agent with the Coordinator via HTTP POST.
func (c *Client) Register(ctx context.Context) (*RegistrationResult, error) {
	body := map[string]any{
		"agent_id":     c.config.AgentID,
		"name":         c.config.AgentName,
		"agent_type":   c.config.AgentType,
		"capabilities": c.config.Capabilities,
		"model":        c.config.Model,
	}
	data, err := c.httpPost(ctx, "/api/v1/agents/register", body)
	if err != nil {
		return nil, fmt.Errorf("register: %w", err)
	}
	var result RegistrationResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("register: decode: %w", err)
	}
	c.config.AgentToken = result.AgentToken
	return &result, nil
}

// Run starts the main event loop, reading WS messages until context cancels.
func (c *Client) Run(ctx context.Context) error {
	c.mu.Lock()
	conn := c.wsConn
	c.mu.Unlock()
	if conn == nil {
		return fmt.Errorf("not connected: call Connect() before Run()")
	}
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-c.done:
			return nil
		default:
		}
		_, msg, err := conn.ReadMessage()
		if err != nil {
			if c.connected {
				log.Printf("ws read error: %v", err)
			}
			return err
		}
		c.handleMessage(msg)
	}
}
