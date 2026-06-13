# DESIGN-phase14-workspace.md — Phase 14: Shared Workspace

> Version: v0.14.0-draft | Date: 2026-06-13 | Author: planner

## Background

Agora currently manages messages and task assignment, but not files. Agents on the
same machine can collaborate on code/docs via the local filesystem, but
distributed agents on different hosts have no shared file system. This is a
blocker for true distributed multi-agent collaboration.

The task requires a **Shared Workspace service** that lets any agent, regardless
of host, read and write the same project files (code, docs, PPT, spreadsheets,
etc.) — the equivalent of Google Drive or Notion but consumed by agents, not
humans.

### Why Not Git

Git manages code well but cannot handle binary files (PPT, spreadsheets, PDFs,
images) effectively. A Workspace must natively support all file types.

### Why Not Existing Artifact Storage

Phase 12.5a introduced `project_artifacts` — a simple key-value BLOB store for
agent notes and findings. It is NOT a file system:
- No directory hierarchy
- No partial reads/writes
- No file locking
- No streaming for large files
- BLOBs stored in SQLite (not scalable for large files)

Workspace is a superset: it provides a full virtual filesystem with directories,
file metadata, locking, and pluggable storage backends.

## Direction Evaluation

| Direction | Importance | Urgency | Feasibility | Complexity | Recommendation |
|---|---|---|---|---|---|
| Workspace API (CRUD + dirs + locks) | ★★★★★ | ★★★★★ | ★★★★★ | Medium | **Phase 14 Core** |
| Pluggable Storage Backend | ★★★★★ | ★★★★ | ★★★★ | Medium | **Phase 14 Core** |
| Pipeline Integration | ★★★★★ | ★★★★★ | ★★★★ | Low | **Phase 14 Core** |
| File Versioning | ★★★ | ★★ | ★★★ | Medium | Defer to Phase 14+ |
| WebDAV/FUSE Mount | ★★ | ★ | ★★ | High | Defer (nice-to-have) |

### Why Workspace First (Before Postgres/K8s)

1. **Distributed agent prerequisite** — Without shared files, distributed agents
   can only talk, not build. Workspace is the foundation for any multi-host
   deployment.
2. **Pipeline needs it** — The full-auto dev loop (Phase 13) currently assumes
   agents share a local filesystem. Workspace makes this work across hosts.
3. **All file types** — Unlike Git, Workspace handles code, docs, PPT, images,
   spreadsheets, and any binary format.
4. **Builds on existing infra** — Reuses the agent auth protocol, RBAC, and
   storage patterns already in place.

## Design Overview

```
┌──────────────────────────────────────────────────┐
│                  Agora Coordinator                │
│  ┌─────────────┐  ┌──────────────┐               │
│  │ Workspace   │  │ Workspace    │               │
│  │ REST API    │  │ WS Messages  │               │
│  └──────┬──────┘  └──────┬───────┘               │
│         │                │                       │
│  ┌──────▼────────────────▼───────┐               │
│  │     WorkspaceManager          │               │
│  │  - file CRUD + metadata       │               │
│  │  - directory tree             │               │
│  │  - file locking               │               │
│  │  - access control (RBAC)      │               │
│  └──────────────┬────────────────┘               │
│                 │                                │
│  ┌──────────────▼────────────────┐               │
│  │     StorageBackend (ABC)      │               │
│  │  - LocalFileBackend           │               │
│  │  - S3Backend (MinIO/AWS)      │               │
│  └──────────────┬────────────────┘               │
│                 │                                │
│  ┌──────────────▼────────────────┐               │
│  │     SQLite (metadata only)    │               │
│  │  - file_nodes table           │               │
│  │  - file_locks table           │               │
│  └───────────────────────────────┘               │
└──────────────────────────────────────────────────┘
         │                          │
         │ REST                     │ WebSocket
         ▼                          ▼
   ┌──────────┐              ┌──────────┐
   │ Agent A  │              │ Agent B  │
   │ (Host 1) │              │ (Host 2) │
   └──────────┘              └──────────┘
```

Key principle: **metadata in SQLite, content in backend**. The database stores
file paths, sizes, types, timestamps, and lock state. The actual file bytes live
in the configured storage backend (local disk or S3-compatible object store).

## Part A: Data Model

### A.1 FileNode

```python
class FileType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"

class FileNode(BaseModel):
    """A node in the workspace virtual filesystem."""
    id: str                          # UUID
    project_id: str                  # tenant/project namespace
    path: str                        # e.g. "src/main.py" (relative, /-separated)
    name: str                        # e.g. "main.py"
    file_type: FileType              # file | directory
    parent_path: str | None          # e.g. "src" (None for root)
    size: int = 0                    # bytes (0 for directories)
    content_type: str = "application/octet-stream"
    checksum_sha256: str | None = None
    created_by: str                  # agent_id
    created_at: datetime
    updated_at: datetime
    version: int = 1                 # monotonically increasing
```

### A.2 FileLock

```python
class LockType(str, Enum):
    READ = "read"                    # shared: multiple readers
    WRITE = "write"                  # exclusive: one writer, no readers

class FileLock(BaseModel):
    """Tracks an active file lock for concurrency control."""
    id: str                          # UUID
    file_id: str                     # FK → file_nodes.id
    project_id: str
    path: str                        # denormalized for fast lookup
    lock_type: LockType
    held_by: str                     # agent_id
    acquired_at: datetime
    expires_at: datetime             # auto-release on expiry (default 5 min)
```

### A.3 SQLite Schema

```sql
-- Schema version 14 → 15 migration

CREATE TABLE IF NOT EXISTS file_nodes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'file',   -- 'file' | 'directory'
    parent_path TEXT,
    size INTEGER NOT NULL DEFAULT 0,
    content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    checksum_sha256 TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(project_id, path)
);

CREATE INDEX IF NOT EXISTS idx_file_nodes_project ON file_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_file_nodes_parent ON file_nodes(project_id, parent_path);
CREATE INDEX IF NOT EXISTS idx_file_nodes_type ON file_nodes(project_id, file_type);

CREATE TABLE IF NOT EXISTS file_locks (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    path TEXT NOT NULL,
    lock_type TEXT NOT NULL DEFAULT 'write',   -- 'read' | 'write'
    held_by TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES file_nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_locks_path ON file_locks(project_id, path);
CREATE INDEX IF NOT EXISTS idx_file_locks_holder ON file_locks(held_by);
```

## Part B: Storage Backend

### B.1 Backend ABC

```python
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    """Pluggable storage for workspace file content."""

    @abstractmethod
    async def put(self, project_id: str, path: str,
                  content: bytes, content_type: str) -> str:
        """Store file content. Returns checksum_sha256."""
        ...

    @abstractmethod
    async def get(self, project_id: str, path: str) -> bytes | None:
        """Retrieve file content. Returns None if not found."""
        ...

    @abstractmethod
    async def delete(self, project_id: str, path: str) -> bool:
        """Delete file content. Returns True if existed."""
        ...

    @abstractmethod
    async def exists(self, project_id: str, path: str) -> bool:
        """Check if file content exists."""
        ...

    @abstractmethod
    async def get_range(self, project_id: str, path: str,
                        offset: int, length: int) -> bytes:
        """Read a byte range (for large file streaming)."""
        ...
```

### B.2 LocalFileBackend

```python
class LocalFileBackend(StorageBackend):
    """Stores files on the local filesystem under a root directory."""

    def __init__(self, root: str = "./data/workspaces"):
        self.root = Path(root)

    def _resolve(self, project_id: str, path: str) -> Path:
        # Normalize: strip leading /, prevent traversal
        safe = path.lstrip("/").replace("..", "")
        return (self.root / project_id / safe).resolve()

    async def put(self, project_id, path, content, content_type):
        full = self._resolve(project_id, path)
        full.parent.mkdir(parents=True, exist_ok=True)
        await aiofiles.write(full, content)  # or sync for simplicity
        return hashlib.sha256(content).hexdigest()
    # ... etc
```

### B.3 S3Backend (MinIO / AWS S3)

```python
class S3Backend(StorageBackend):
    """Stores files in S3-compatible object storage."""

    def __init__(self, endpoint: str, bucket: str,
                 access_key: str, secret_key: str):
        self.client = aioboto3.client("s3", ...)
        self.bucket = bucket

    def _key(self, project_id: str, path: str) -> str:
        return f"{project_id}/{path.lstrip('/')}"

    async def put(self, project_id, path, content, content_type):
        key = self._key(project_id, path)
        sha = hashlib.sha256(content).hexdigest()
        await self.client.put_object(
            Bucket=self.bucket, Key=key, Body=content,
            ContentType=content_type, Metadata={"sha256": sha},
        )
        return sha
    # ... etc
```

### B.4 Backend Selection

```yaml
# config.yaml
workspace:
  backend: local              # local | s3
  local:
    root: ./data/workspaces
  s3:
    endpoint: http://minio:9000
    bucket: agora-workspaces
    access_key: ${MINIO_ACCESS_KEY}
    secret_key: ${MINIO_SECRET_KEY}
```

Default is `local` — zero-config for single-host deployments. `s3` enables
multi-host shared storage via MinIO or AWS S3.

## Part C: WorkspaceManager

### C.1 Core Operations

```python
class WorkspaceManager:
    """Orchestrates file CRUD, directory operations, and locking."""

    def __init__(self, storage: Storage, backend: StorageBackend):
        self.storage = storage      # SQLite metadata
        self.backend = backend      # file content

    # ── File CRUD ──

    async def write_file(self, project_id: str, path: str,
                         content: bytes, agent_id: str,
                         content_type: str = "application/octet-stream",
                         lock_id: str | None = None) -> FileNode:
        """Create or overwrite a file. Requires write lock if locked."""
        ...

    async def read_file(self, project_id: str, path: str,
                        agent_id: str) -> tuple[FileNode, bytes]:
        """Read file metadata + content."""
        ...

    async def read_file_range(self, project_id: str, path: str,
                              offset: int, length: int,
                              agent_id: str) -> bytes:
        """Read a byte range (streaming support)."""
        ...

    async def delete_file(self, project_id: str, path: str,
                          agent_id: str) -> bool:
        """Delete a file. Fails if locked by another agent."""
        ...

    async def stat(self, project_id: str, path: str) -> FileNode | None:
        """Get file metadata without content."""
        ...

    # ── Directory Operations ──

    async def list_dir(self, project_id: str, path: str = "",
                       recursive: bool = False) -> list[FileNode]:
        """List directory contents."""
        ...

    async def mkdir(self, project_id: str, path: str,
                    agent_id: str) -> FileNode:
        """Create a directory (idempotent)."""
        ...

    async def rmdir(self, project_id: str, path: str,
                    agent_id: str) -> bool:
        """Remove empty directory."""
        ...

    # ── Locking ──

    async def acquire_lock(self, project_id: str, path: str,
                           agent_id: str, lock_type: LockType,
                           ttl_seconds: int = 300) -> FileLock:
        """Acquire a read or write lock. Blocks if conflict."""
        ...

    async def release_lock(self, lock_id: str, agent_id: str) -> bool:
        """Release a held lock."""
        ...

    async def check_lock(self, project_id: str,
                         path: str) -> FileLock | None:
        """Check if a file is currently locked."""
        ...

    # ── Bulk Operations ──

    async def pull(self, project_id: str, paths: list[str],
                   agent_id: str) -> dict[str, bytes]:
        """Bulk read multiple files (for task bootstrap)."""
        ...

    async def push(self, project_id: str,
                   files: dict[str, bytes],
                   agent_id: str) -> list[FileNode]:
        """Bulk write multiple files (for task completion)."""
        ...
```

### C.2 Locking Semantics

```
Lock compatibility matrix:

         | READ lock  | WRITE lock | No lock
---------|------------|------------|---------
READ     | ✅ shared  | ❌ blocked | ✅
WRITE    | ❌ blocked | ❌ blocked | ✅
No lock  | ✅         | ✅         | ✅
```

- **Read lock**: multiple agents can hold read locks simultaneously
- **Write lock**: exclusive — no other read or write locks allowed
- **Lock expiry**: auto-released after TTL (default 5 min). Agents should
  refresh locks periodically for long operations.
- **Lock enforcement**: checked on every write_file() and delete_file().
  read_file() is always allowed (reads don't conflict with writes at the
  Workspace level — eventual consistency is acceptable for agent workflows).

### C.3 Lock Workflow

```
Agent A: acquire_lock(path="src/main.py", type=WRITE) → granted
Agent B: acquire_lock(path="src/main.py", type=WRITE) → blocked (409 Conflict)
Agent B: acquire_lock(path="src/main.py", type=READ)  → blocked (409 Conflict)
Agent A: write_file(path="src/main.py", content=..., lock_id=...) → success
Agent A: release_lock(lock_id) → released
Agent B: acquire_lock(path="src/main.py", type=WRITE) → granted (now available)
```

### C.4 Agent Workflow (Task Execution)

```
1. Agent receives TASK_ASSIGNED (includes workspace_paths hint)
2. Agent: POST /api/v1/workspaces/{project}/pull  → downloads needed files
3. Agent: POST /api/v1/workspaces/{project}/locks  → acquires write locks
4. Agent: edits files locally
5. Agent: POST /api/v1/workspaces/{project}/push   → uploads changed files
6. Agent: POST /api/v1/workspaces/{project}/locks/{id}/release → releases locks
7. Agent: sends TASK_COMPLETED with artifact_paths
```

## Part D: REST API

### D.1 Endpoints

```
# File operations
POST   /api/v1/workspaces/{project_id}/files/{path:path}
       → write_file (body: raw bytes, query: ?lock_id=)
GET    /api/v1/workspaces/{project_id}/files/{path:path}
       → read_file (header: Range: bytes=0-1023 for partial)
DELETE /api/v1/workspaces/{project_id}/files/{path:path}
       → delete_file
HEAD   /api/v1/workspaces/{project_id}/files/{path:path}
       → stat (metadata only)

# Directory operations
GET    /api/v1/workspaces/{project_id}/tree?path=&recursive=false
       → list_dir
POST   /api/v1/workspaces/{project_id}/dirs/{path:path}
       → mkdir
DELETE /api/v1/workspaces/{project_id}/dirs/{path:path}
       → rmdir

# Locking
POST   /api/v1/workspaces/{project_id}/locks
       → acquire_lock (body: {path, lock_type, ttl_seconds})
DELETE /api/v1/workspaces/{project_id}/locks/{lock_id}
       → release_lock
GET    /api/v1/workspaces/{project_id}/locks?path=
       → check_lock

# Bulk operations
POST   /api/v1/workspaces/{project_id}/pull
       → bulk read (body: {paths: [...]})
POST   /api/v1/workspaces/{project_id}/push
       → bulk write (multipart: file fields = paths)
```

### D.2 Request/Response Examples

```
# Write a file
POST /api/v1/workspaces/myproject/files/src/main.py
Authorization: Bearer ag-xxx
Content-Type: application/octet-stream

<raw file bytes>

→ 201
{
  "id": "uuid",
  "path": "src/main.py",
  "size": 1234,
  "checksum_sha256": "abc...",
  "version": 2
}

# Read a file
GET /api/v1/workspaces/myproject/files/src/main.py
→ 200 (body = raw bytes, headers: X-Checksum-SHA256, X-Version)

# List directory
GET /api/v1/workspaces/myproject/tree?path=src
→ 200
{
  "path": "src",
  "entries": [
    {"path": "src/main.py", "file_type": "file", "size": 1234},
    {"path": "src/utils", "file_type": "directory", "size": 0},
    {"path": "src/utils/helpers.py", "file_type": "file", "size": 567}
  ]
}

# Acquire lock
POST /api/v1/workspaces/myproject/locks
{"path": "src/main.py", "lock_type": "write", "ttl_seconds": 300}

→ 201
{"id": "lock-uuid", "path": "src/main.py", "lock_type": "write",
 "held_by": "agent-1", "expires_at": "2026-06-13T10:05:00Z"}

# Bulk pull (task bootstrap)
POST /api/v1/workspaces/myproject/pull
{"paths": ["src/main.py", "src/utils/helpers.py", "docs/README.md"]}

→ 200 (multipart/mixed or JSON with base64-encoded content)
```

## Part E: WebSocket Messages

For real-time lock notifications and file change events:

```python
# New MessageType enum values
WORKSPACE_FILE_CHANGED = "WORKSPACE_FILE_CHANGED"    # server→agents
WORKSPACE_LOCK_ACQUIRED = "WORKSPACE_LOCK_ACQUIRED"  # server→agents
WORKSPACE_LOCK_RELEASED = "WORKSPACE_LOCK_RELEASED"  # server→agents
WORKSPACE_LOCK_EXPIRED = "WORKSPACE_LOCK_EXPIRED"    # server→lock holder
```

```
# File changed notification (broadcast to project agents)
→ {"type": "WORKSPACE_FILE_CHANGED",
   "payload": {"project_id": "p1", "path": "src/main.py",
               "agent_id": "agent-1", "version": 3}}

# Lock acquired notification
→ {"type": "WORKSPACE_LOCK_ACQUIRED",
   "payload": {"project_id": "p1", "path": "src/main.py",
               "lock_type": "write", "held_by": "agent-1"}}

# Lock expired warning (to lock holder)
→ {"type": "WORKSPACE_LOCK_EXPIRED",
   "payload": {"lock_id": "...", "path": "src/main.py"}}
```

## Part F: Pipeline Integration

### F.1 Current State (Phase 13)

Pipeline EXECUTING phase calls `orch.parallel.execute_graph(graph)`. Agents
receive TASK_ASSIGNED messages and work on local files. artifact_paths are
recorded but not managed by Agora.

### F.2 Target State (Phase 14)

Pipeline EXECUTING phase integrates with Workspace:

```
1. DECOMPOSING phase → task graph generated
   → WorkspaceManager.mkdir() for project root if not exists

2. EXECUTING phase → for each task:
   a. TASK_ASSIGNED includes workspace_paths hint
      (files the task is expected to read/write, from artifact_paths)
   b. Agent pulls files via Workspace API
   c. Agent acquires write locks on files it will modify
   d. Agent edits locally
   e. Agent pushes changes via Workspace API
   f. Agent releases locks
   g. Agent sends TASK_COMPLETED with artifact_paths

3. REVIEWING phase → reviewer pulls all changed files from Workspace
4. RELEASING phase → releaser pulls files, commits to git, tags release
```

### F.3 Changes to PipelineExecutor

```python
# pipeline_executor.py — EXECUTING phase
async def execute_phases(orch, run):
    # ... discuss, decompose ...
    
    # EXECUTING: inject workspace context
    run.phase = PipelinePhase.EXECUTING
    ws_manager = orch.workspace_manager  # new dependency
    
    # Pre-populate workspace with initial files if needed
    await ws_manager.mkdir(run.project_id, "", agent_id="coordinator")
    
    # Augment graph tasks with workspace_paths
    for task in graph.tasks:
        task.workspace_paths = task.artifact_paths  # files to work on
    
    results = await orch.parallel.execute_graph(graph)
    # ... review, release ...
```

### F.4 Changes to TaskNode

```python
class TaskNode(BaseModel):
    # ... existing fields ...
    workspace_paths: list[str] = Field(default_factory=list)
    # Files this task is expected to read/write.
    # Set by DECOMPOSING phase, used by agent to pull/push.
```

## Part G: RBAC Integration

Workspace operations reuse the existing RBAC system (Phase 10.2):

```python
# New permissions
Permission.WORKSPACE_READ = "workspace:read"
Permission.WORKSPACE_WRITE = "workspace:write"
Permission.WORKSPACE_ADMIN = "workspace:admin"  # manage locks, delete any file

# Role updates
DEFAULT_ROLES = {
    "admin": [..., "workspace:read", "workspace:write", "workspace:admin"],
    "agent": [..., "workspace:read", "workspace:write"],
    "observer": [..., "workspace:read"],
}
```

Endpoints decorated with `@requires(Permission.WORKSPACE_READ)` etc.

## Part H: Implementation Plan

### H.1 Task Breakdown

| ID | Task | Assignee | Est. | Depends On |
|----|------|----------|------|------------|
| 14.1a | FileNode + FileLock models | dev-merger | 0.5d | — |
| 14.1b | SQLite schema migration (v14→v15) | dev-merger | 0.5d | 14.1a |
| 14.1c | StorageBackend ABC + LocalFileBackend | dev-merger | 1d | — |
| 14.1d | S3Backend (MinIO) | dev-merger | 1d | 14.1c |
| 14.2a | WorkspaceManager: file CRUD | dev-merger | 1.5d | 14.1b, 14.1c |
| 14.2b | WorkspaceManager: directory ops | dev-merger | 0.5d | 14.2a |
| 14.2c | WorkspaceManager: locking | dev-merger | 1d | 14.2a |
| 14.2d | WorkspaceManager: bulk pull/push | dev-merger | 0.5d | 14.2a |
| 14.3a | REST API: file endpoints | dev-merger | 1d | 14.2a |
| 14.3b | REST API: dir + lock endpoints | dev-merger | 0.5d | 14.2b, 14.2c |
| 14.3c | REST API: bulk endpoints | dev-merger | 0.5d | 14.2d |
| 14.4a | WS messages: file change + lock events | dev-merger | 0.5d | 14.2c |
| 14.5a | Pipeline integration | dev-merger | 1d | 14.3a-c |
| 14.5b | TaskNode.workspace_paths | dev-merger | 0.5d | 14.5a |
| 14.6a | RBAC: workspace permissions | dev-merger | 0.5d | 14.3a |
| 14.7a | Unit tests: WorkspaceManager | dev-merger | 1d | 14.2a-d |
| 14.7b | Unit tests: REST API | dev-merger | 1d | 14.3a-c |
| 14.7c | Integration tests: Pipeline + Workspace | dev-merger | 1d | 14.5a |
| 14.8a | Docs: API.md update | dev-merger | 0.5d | 14.3a-c |
| 14.8b | Docs: ARCHITECTURE.md update | dev-merger | 0.5d | all |

**Total: ~14 dev days** (can be parallelized where dependencies allow)

### H.2 Phased Rollout

1. **Week 1**: Models + LocalFileBackend + WorkspaceManager core (14.1a-c, 14.2a-d)
2. **Week 2**: REST API + WS messages + tests (14.3a-c, 14.4a, 14.7a-b)
3. **Week 3**: Pipeline integration + RBAC + S3Backend (14.5a-b, 14.6a, 14.1d)
4. **Week 4**: Integration tests + docs (14.7c, 14.8a-b)

## Part I: Design Decisions

1. **Metadata in SQLite, content in backend** — SQLite is great for structured
   metadata queries (list dir, find by path). BLOBs in SQLite don't scale.
   Separating metadata from content lets us keep SQLite while supporting S3 for
   multi-host deployments.

2. **Path-based API, not ID-based** — Agents think in file paths
   ("src/main.py"), not UUIDs. The API uses paths directly, with project_id as
   namespace. This mirrors how agents actually work.

3. **Read locks are advisory, write locks are enforced** — Reads don't block
   each other. Write locks are enforced on write/delete. This matches the agent
   workflow: multiple agents can read the same file, but only one edits at a
   time.

4. **Lock expiry with refresh** — Locks auto-expire after TTL to prevent
   deadlocks from crashed agents. Long-running operations should refresh locks
   periodically.

5. **Bulk pull/push for task workflow** — The most common pattern is "pull
   files at task start, push changes at task end". Bulk endpoints optimize this.

6. **Local backend as default** — Zero-config for the common case (single-host
   or shared NFS). S3 backend for truly distributed deployments.

7. **No file versioning in v1** — Version field exists in the model but
   version history is deferred. The `version` counter helps detect concurrent
   modifications (optimistic concurrency: "write failed, file version changed
   from 3 to 4, please re-pull").

8. **Optimistic concurrency via version field** — write_file() checks that the
   client's expected version matches the current version. If not, the file was
   modified by another agent (outside the lock system or lock expired), and the
   write is rejected with 409 Conflict.

## Part J: Edge Cases

1. **Lock expired during write** — write_file() checks lock validity. If
   expired, rejects with 409 "lock expired". Agent must re-acquire.

2. **Concurrent directory creation** — mkdir() is idempotent. If directory
   already exists, returns existing node (200, not 201).

3. **Delete non-empty directory** — rmdir() fails with 409 "directory not
   empty". Agent must delete children first.

4. **Path traversal attacks** — All paths are normalized (strip `..`, resolve
   relative segments). Backend resolves to a sandboxed root.

5. **Large file streaming** — GET with Range header for partial reads. PUT
   accepts streaming body. Backend implementations should not buffer entire
   file in memory.

6. **Agent crash with held locks** — Lock expiry (TTL) auto-releases. Next
   agent to acquire gets the lock. Crashed agent's partial writes are not
   committed (write is atomic at the backend level).

7. **Project isolation** — All paths are scoped to project_id. Agent from
   project A cannot access project B's files (enforced by RBAC + path prefix).

8. **Backend migration** — Switching from local to S3 requires migrating
   existing files. A migration script copies files from old backend to new,
   then updates config. Metadata in SQLite is unchanged.

## References

- Google Drive API v3: files resource with parents, mimeType, checksums
- Notion API: file objects with external/file_upload/file types
- MinIO Python SDK: S3-compatible put_object/get_object with metadata
- Existing Agora patterns: Storage class, schema migrations, RBAC decorators
