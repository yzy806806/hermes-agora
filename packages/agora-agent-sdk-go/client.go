package agorasdk

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// Client is the main SDK client for connecting agents to Agora.
type Client struct {
	config     AgentConfig
	wsConn     *websocket.Conn
	httpClient *http.Client
	connected  bool
	mu         sync.Mutex
	done       chan struct{}
	// OnTaskAssigned is called when a TASK_ASSIGNED message arrives.
	// The raw payload is provided for the caller to decode.
	OnTaskAssigned func(raw json.RawMessage)
	// OnDiscussionMessage is called when a SPEECH_ADDED message arrives.
	// The raw payload is provided for the caller to decode.
	OnDiscussionMessage func(raw json.RawMessage)
}

// NewClient creates a new Agora SDK client with the given config.
func NewClient(config AgentConfig) *Client {
	if config.HeartbeatInterval == 0 {
		config.HeartbeatInterval = 30 * time.Second
	}
	if config.MaxRetries == 0 {
		config.MaxRetries = 3
	}
	return &Client{
		config:     config,
		httpClient: defaultHTTPClient(),
		done:       make(chan struct{}),
	}
}

// Connect opens a WebSocket to the Coordinator and starts heartbeat.
func (c *Client) Connect(ctx context.Context) error {
	wsURL := c.wsURL()
	conn, _, err := websocket.DefaultDialer.DialContext(ctx, wsURL, nil)
	if err != nil {
		return fmt.Errorf("connect: %w", err)
	}
	c.mu.Lock()
	c.wsConn = conn
	c.connected = true
	c.mu.Unlock()
	go c.heartbeatLoop()
	return nil
}

// Disconnect closes the WebSocket connection.
func (c *Client) Disconnect() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.connected = false
	close(c.done)
	if c.wsConn != nil {
		_ = c.wsConn.WriteMessage(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
		)
		c.wsConn.Close()
		c.wsConn = nil
	}
	return nil
}
