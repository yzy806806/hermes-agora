package agorasdk

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/gorilla/websocket"
)

// CreateMotion creates a new discussion motion via HTTP.
func (c *Client) CreateMotion(ctx context.Context, title, desc string) (*MotionResult, error) {
	body := map[string]any{
		"title":       title,
		"description": desc,
	}
	data, err := c.httpPost(ctx, "/api/v1/motions", body)
	if err != nil {
		return nil, fmt.Errorf("create_motion: %w", err)
	}
	var result MotionResult
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("create_motion: decode: %w", err)
	}
	return &result, nil
}

// Speak sends a speech in a discussion round via WebSocket.
func (c *Client) Speak(ctx context.Context, motionID, content string) (*SpeechResult, error) {
	msg := NewWSMessage(Speak, map[string]any{
		"motion_id": motionID,
		"content":   content,
	})
	if err := c.sendWS(msg); err != nil {
		return nil, fmt.Errorf("speak: %w", err)
	}
	return &SpeechResult{Success: true}, nil
}

// Vote casts a vote on a motion via WebSocket.
func (c *Client) Vote(ctx context.Context, motionID, choice string) (*VoteResult, error) {
	msg := NewWSMessage(Vote, map[string]any{
		"motion_id": motionID,
		"vote":      choice,
	})
	if err := c.sendWS(msg); err != nil {
		return nil, fmt.Errorf("vote: %w", err)
	}
	return &VoteResult{Success: true}, nil
}

// sendWS writes a WSMessage as JSON to the WebSocket connection.
func (c *Client) sendWS(msg *WSMessage) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.wsConn == nil {
		return fmt.Errorf("not connected — call Connect() first")
	}
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	return c.wsConn.WriteMessage(websocket.TextMessage, data)
}
