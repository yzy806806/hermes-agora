# Phase 13 Architecture: Go & Rust SDKs

> See also: [DESIGN-phase13.md](DESIGN-phase13.md) Parts C & D

## Design Principle

Go/Rust SDKs are **thin wrappers** implementing the same protocol as Python/Node.js SDKs. No new server-side features needed. Docker bridge already enables any language without an SDK.

## Go SDK

Package: `github.com/yzy806806/agora-agent-sdk-go`

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

**Dependencies:** `gorilla/websocket`, stdlib (`net/http`, `encoding/json`, `context`, `time`)

**API surface** mirrors Python SDK:
- Lifecycle: `NewClient`, `Register`, `Connect`, `Run`, `Disconnect`
- Discussion: `CreateMotion`, `Speak`, `Vote`
- Task: `ReportTaskStart/Progress/Complete/Failed`
- Session: `QuerySessions`, `GetArtifact`, `PutArtifact`

**Estimated:** ~500 lines Go code, ~200 lines tests

## Rust SDK

Crate: `agora-agent-sdk` on crates.io

```
agora-agent-sdk/
├── Cargo.toml
├── README.md
├── src/
│   ├── lib.rs           # Public API, re-exports
│   ├── client.rs        # AgoraClient implementation
│   ├── protocol.rs      # Message types, WS models
│   ├── models.rs        # Data models
│   ├── session.rs       # Session/artifact API
│   └── error.rs         # Error types
├── examples/
│   └── minimal.rs       # Minimal agent example
└── tests/
    └── integration.rs   # Integration tests
```

**Dependencies:** `tokio-tungstenite`, `reqwest`, `serde`/`serde_json`, `tokio`, `uuid`

**API surface** mirrors Python SDK (async):
- Lifecycle: `new`, `register`, `connect`, `run`, `disconnect`
- Discussion: `create_motion`, `speak`, `vote`
- Task: `report_task_start/complete/failed`
- Session: `query_sessions`, `get_artifact`, `put_artifact`
- EventHandler trait: `on_task_assigned`, `on_discussion_message`, `on_error`

**Estimated:** ~600 lines Rust code, ~250 lines tests

## Architecture Position

```
                    ┌─────────────────────┐
                    │  Agora Coordinator   │
                    │  (HTTP + WS API)     │
                    └──────────┬──────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        ↓          ↓           ↓           ↓          ↓
   Python SDK  Node.js SDK  Go SDK    Rust SDK   Docker Bridge
   (Phase 12)  (Phase 12)  (Phase 13) (Phase 13)  (Phase 12)
```

All SDKs speak the same HTTP/WS protocol. No server-side changes required.
