package agorasdk

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// wsURL builds the WebSocket endpoint URL from config.
func (c *Client) wsURL() string {
	host := strings.TrimPrefix(c.config.CoordinatorURL, "http://")
	host = strings.TrimPrefix(host, "https://")
	base := fmt.Sprintf("ws://%s/ws/%s", host, c.config.AgentID)
	if c.config.AgentToken != "" {
		base += "?token=" + c.config.AgentToken
	}
	return base
}

// heartbeatLoop sends periodic heartbeat messages.
func (c *Client) heartbeatLoop() {
	ticker := time.NewTicker(c.config.HeartbeatInterval)
	defer ticker.Stop()
	for range ticker.C {
		c.mu.Lock()
		conn := c.wsConn
		connected := c.connected
		c.mu.Unlock()
		if !connected || conn == nil {
			return
		}
		msg := NewWSMessage(Heartbeat, map[string]any{})
		data, _ := json.Marshal(msg)
		if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
			log.Printf("heartbeat error: %v", err)
			return
		}
	}
}

// handleMessage dispatches an incoming WS message.
func (c *Client) handleMessage(raw []byte) {
	var msg WSMessage
	if err := json.Unmarshal(raw, &msg); err != nil {
		log.Printf("invalid ws message: %v", err)
		return
	}
	log.Printf("received: %s", msg.Type)
	if msg.Type == TaskAssigned && c.OnTaskAssigned != nil {
		c.OnTaskAssigned(msg.Payload)
	}
	if msg.Type == SpeechAdded && c.OnDiscussionMessage != nil {
		c.OnDiscussionMessage(msg.Payload)
	}
}
