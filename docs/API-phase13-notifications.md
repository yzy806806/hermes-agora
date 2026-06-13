# Phase 13: Notification API

> 版本: v0.13.0 | 基础路径: `/api/v1`

## GET /notifications

列出通知。

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `project_id` | string | null | 过滤特定项目 |
| `unread_only` | bool | false | 仅返回未读通知 |
| `priority` | string | null | 过滤优先级 (critical/high/medium/low) |
| `limit` | int | 50 | 返回数量上限 |
| `offset` | int | 0 | 偏移量 |

**响应**:
```json
{
  "notifications": [
    {
      "id": "notif-xxx",
      "type": "PIPELINE_COMPLETED",
      "title": "Pipeline 完成",
      "body": "Pipeline pipe-xxx 已成功完成，发布 v0.13.0",
      "project_id": "agora-project",
      "priority": "high",
      "read": false,
      "created_at": "2026-06-12T11:00:00Z"
    }
  ],
  "total": 12,
  "unread_count": 3
}
```

---

## POST /notifications/{id}/read

标记单条通知为已读。

**响应**: `{\"id\": \"notif-xxx\", \"read\": true}`

**状态码**:
- `200` — 标记成功
- `404` — 通知不存在

---

## POST /notifications/read-all

标记所有通知为已读。

**请求体**（可选）:
```json
{
  "project_id": "agora-project"
}
```

不传 `project_id` 时标记所有项目的通知为已读。

**响应**: `{\"marked_count\": 5}`

---

## 通知类型

| Type | 触发条件 | 默认优先级 |
|------|----------|-----------|
| `PIPELINE_COMPLETED` | Pipeline 成功完成 | high |
| `PIPELINE_FAILED` | Pipeline 失败 | critical |
| `REVIEW_REQUESTED` | 需要代码审查 | medium |
| `AGENT_OFFLINE` | Agent 心跳丢失 | high |
| `RATE_LIMITED` | Agent 触发速率限制 | medium |
| `DISCUSSION_DEADLOCK` | 讨论陷入僵局 | medium |

## Notification WebSocket 消息

通知通过 Dashboard WebSocket 实时推送：

```json
{
  "type": "NOTIFICATION",
  "payload": {
    "id": "notif-xxx",
    "type": "PIPELINE_COMPLETED",
    "title": "Pipeline 完成",
    "body": "Pipeline pipe-xxx 已成功完成",
    "project_id": "agora-project",
    "priority": "high",
    "created_at": "2026-06-12T11:00:00Z"
  }
}
```
