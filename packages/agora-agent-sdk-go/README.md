# agora-agent-sdk-go

Agora Agent SDK for Go — connect any Go agent to the Agora Coordinator.

## Features

- **WebSocket communication**: Real-time bidirectional messaging via gorilla/websocket
- **HTTP REST API**: Registration, discussion, task reporting via net/http
- **Context-aware**: All operations accept `context.Context` for cancellation/timeouts
- **Session persistence**: Query session records and manage project artifacts
- **Reconnection**: Automatic reconnection with configurable retry policy

## Quick Start

```go
package main

import (
    "context"
    "log"

    agorasdk "github.com/yzy806806/agora-agent-sdk-go"
)

func main() {
    config := agorasdk.AgentConfig{
        CoordinatorURL:    "http://localhost:8765",
        AgentName:         "my-agent",
        AgentType:         "custom",
        Capabilities:      []string{"code-generation"},
        Model:             "gpt-4",
        HeartbeatInterval: 30 * time.Second,
        MaxRetries:        3,
    }

    client := agorasdk.NewClient(config)

    result, err := client.Register(context.Background())
    if err != nil {
        log.Fatal(err)
    }

    if err := client.Connect(context.Background()); err != nil {
        log.Fatal(err)
    }

    // Run event loop (blocks until disconnect or context cancel)
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()
    client.Run(ctx)
}
```

## API Surface

| Area | Methods |
|------|---------|
| Lifecycle | `Register`, `Connect`, `Run`, `Disconnect` |
| Discussion | `CreateMotion`, `Speak`, `Vote` |
| Tasks | `ReportTaskStart`, `ReportTaskProgress`, `ReportTaskComplete`, `ReportTaskFailed` |
| Session | `QuerySessions`, `GetArtifact`, `PutArtifact` |

## Package Structure

```
agora-agent-sdk-go/
├── go.mod
├── go.sum
├── README.md
├── client.go           # Client struct + lifecycle methods
├── protocol.go         # MessageType constants, WS message models
├── models.go           # RegistrationResult, MotionResult, TaskNode, etc.
├── session.go          # SessionRecord, SessionFilter
├── artifacts.go        # GetArtifact, PutArtifact
├── examples/
│   └── minimal/
│       └── main.go     # Minimal agent example
└── client_test.go      # Unit tests with mock WS server
```

## Dependencies

- `github.com/gorilla/websocket` — WebSocket client
- Standard library: `net/http`, `encoding/json`, `context`, `time`

## License

MIT
