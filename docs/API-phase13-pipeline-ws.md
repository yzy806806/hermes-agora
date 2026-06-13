# Phase 13: Pipeline WebSocket 消息

> 版本: v0.13.0

Pipeline 运行过程中通过 WebSocket 推送到 Dashboard 客户端。

## 服务端→客户端消息

### PIPELINE_PHASE_CHANGE — Pipeline 阶段变更

```json
{
  "type": "PIPELINE_PHASE_CHANGE",
  "payload": {
    "pipeline_id": "pipe-xxx",
    "project_id": "agora-project",
    "old_phase": "discussing",
    "new_phase": "decomposing",
    "timestamp": "2026-06-12T10:05:00Z"
  }
}
```

---

### PIPELINE_TASK_UPDATE — Pipeline 内任务状态更新

```json
{
  "type": "PIPELINE_TASK_UPDATE",
  "payload": {
    "pipeline_id": "pipe-xxx",
    "task_id": "task-001",
    "status": "done",
    "agent_id": "agent-alpha",
    "timestamp": "2026-06-12T10:15:00Z"
  }
}
```

---

### PIPELINE_COMPLETED — Pipeline 完成

```json
{
  "type": "PIPELINE_COMPLETED",
  "payload": {
    "pipeline_id": "pipe-xxx",
    "project_id": "agora-project",
    "outcome": "success",
    "release_version": "v0.13.0",
    "tasks_total": 5,
    "tasks_completed": 5,
    "tasks_failed": 0,
    "duration_seconds": 3600,
    "timestamp": "2026-06-12T11:00:00Z"
  }
}
```

---

### PIPELINE_ERROR — Pipeline 不可重试错误

```json
{
  "type": "PIPELINE_ERROR",
  "payload": {
    "pipeline_id": "pipe-xxx",
    "phase": "executing",
    "error": "All retry attempts exhausted",
    "timestamp": "2026-06-12T10:30:00Z"
  }
}
```

## 代码审查模型

### ReviewRequest

```json
{
  "pipeline_id": "pipe-xxx",
  "changed_files": ["/workspace/auth.py", "/workspace/test_auth.py"],
  "task_results": [
    {"task_id": "task-001", "outcome": "success", "summary": "实现完成"}
  ],
  "test_results": {"passed": 14, "failed": 0}
}
```

### ReviewResult

```json
{
  "pipeline_id": "pipe-xxx",
  "reviewer_id": "reviewer-beta",
  "outcome": "approved",
  "issues": [],
  "summary": "代码质量良好，所有测试通过"
}
```

`outcome` 取值: `approved` | `changes_requested`

### ReviewIssue

```json
{
  "file": "/workspace/auth.py",
  "line": 42,
  "severity": "critical",
  "description": "SQL 注入风险：使用了字符串拼接"
}
```

`severity` 取值: `critical` | `major` | `minor`
