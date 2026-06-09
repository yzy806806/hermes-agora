# Hermes Agora API 参考

> 版本: v0.8.0 | 基础路径: `/api/v1`

## REST API

### Agent 管理

#### POST /agents/register

注册新 Agent 到系统。

**请求体**:
```json
{
  "agent_id": "agent-alpha",
  "name": "Alpha Agent",
  "model": "claude-sonnet-4",
  "hermes_endpoint": "http://localhost:8080",
  "capabilities": ["search", "code"],
  "role": "participant"
}
```

**响应**: `AgentInfo` 对象

**状态码**:
- `200` — 注册成功
- `409` — Agent 已存在

---

#### DELETE /agents/{agent_id}

注销 Agent。

**响应**: `{"status": "ok"}`

**状态码**:
- `200` — 注销成功
- `404` — Agent 不存在

---

#### GET /agents

列出所有已注册 Agent。

**响应**: `AgentInfo[]` 数组

---

### Motion（议题）管理

#### POST /motions

创建新讨论议题。

**请求体**:
```json
{
  "title": "是否采用微服务架构？",
  "description": "讨论单体 vs 微服务的取舍",
  "context": "当前团队 5 人，预计 1 年内扩展到 15 人",
  "rounds": 3,
  "voting_method": "simple_majority",
  "voting_options": null,
  "voting_config": null
}
```

**响应**: `Motion` 对象

**状态码**:
- `200` — 创建成功

---

#### GET /motions

获取议题列表。

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | null | 过滤状态（draft/discussing/voting/closed） |
| `limit` | int | 100 | 返回数量上限 |
| `offset` | int | 0 | 偏移量 |

**响应**:
```json
{
  "motions": [...],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

---

#### GET /motions/{motion_id}

获取议题详情。

**响应**: `Motion` 对象

**状态码**:
- `200` — 成功
- `404` — 议题不存在

---

#### POST /motions/{motion_id}/start

启动讨论（draft → discussing）。

**响应**: `{"status": "started", "current_status": "discussing"}`

**状态码**:
- `200` — 启动成功
- `409` — 状态转换非法
- `404` — 议题不存在

---

### 历史与结果

#### GET /motions/{motion_id}/history

获取讨论历史（消息 + 投票）。

**响应**:
```json
{
  "messages": [
    {
      "id": "msg-001",
      "motion_id": "motion-abc",
      "agent_id": "agent-alpha",
      "round": 1,
      "stance": "support",
      "content": "微服务提供更好的隔离性...",
      "evidence": [...],
      "created_at": "2026-06-08T10:00:00Z"
    }
  ],
  "votes": [
    {
      "agent_id": "agent-alpha",
      "vote": "yes",
      "confidence": 0.85,
      "reason": "..."
    }
  ]
}
```

---

#### GET /motions/{motion_id}/result

获取讨论最终结果。

**响应**:
```json
{
  "motion_id": "motion-abc",
  "decision": "adopted",
  "votes": {"yes": 3, "no": 1, "abstain": 0},
  "rationale": "多数支持，主要论点是...",
  "action_items": ["调研 Kubernetes", "制定迁移计划"]
}
```

**状态码**:
- `200` — 成功
- `400` — 议题尚未关闭
- `404` — 议题不存在

---

### 智能讨论

#### GET /motions/{motion_id}/assessment

获取讨论评估结果。

**响应**:
```json
{
  "motion_id": "motion-abc",
  "result": "consensus_likely",
  "consensus_level": "high",
  "metrics": {
    "agreement_ratio": 0.75,
    "argument_quality": 0.82,
    "participation_rate": 1.0
  },
  "rationale": "多数观点一致，分歧点在...",
  "recommendations": ["可以推进投票"]
}
```

---

#### POST /motions/{motion_id}/force-vote

强制进入投票阶段。

**响应**: `{"status": "voting_started", "current_status": "voting"}`

---

### Bootstrap（自举）

#### POST /bootstrap/triggers

创建自举触发器。

**请求体**:
```json
{
  "topic": "Agora 下一步开发方向",
  "trigger_type": "schedule",
  "config": {"cron": "0 9 * * 1"}
}
```

---

#### POST /bootstrap/approval

提交审批请求。

**请求体**:
```json
{
  "motion_id": "motion-abc",
  "decision": "adopted",
  "rationale": "AI 团队讨论结果：采用微服务"
}
```

---

#### POST /bootstrap/approval/decide

人类审批决策。

**请求体**:
```json
{
  "approval_id": "approval-123",
  "decision": "approved",
  "comment": "同意，按此执行"
}
```

---

## WebSocket 协议

### 连接

```
ws://host:8765/ws/{agent_id}
```

连接后需先发送 REGISTER 消息完成注册，否则部分操作会被拒绝。

### 消息格式

所有消息均为 JSON，包含 `type` 字段标识消息类型。

### 客户端→服务端消息

#### REGISTER — 注册

```json
{
  "type": "REGISTER",
  "agent_id": "agent-alpha",
  "payload": {
    "name": "Alpha Agent",
    "model": "claude-sonnet-4",
    "hermes_endpoint": "http://localhost:8080",
    "capabilities": ["search", "code"],
    "role": "participant"
  }
}
```

#### SPEAK — 发言

```json
{
  "type": "SPEAK",
  "motion_id": "motion-abc",
  "agent_id": "agent-alpha",
  "payload": {
    "round": 1,
    "stance": "support",
    "content": "微服务提供更好的隔离性和独立部署能力",
    "evidence": [
      {"type": "data", "content": "故障隔离率提升 40%"}
    ]
  }
}
```

`stance` 取值: `support` | `oppose` | `neutral`

#### VOTE — 投票

**二值投票**（simple_majority / supermajority / unanimous / weighted）:
```json
{
  "type": "VOTE",
  "motion_id": "motion-abc",
  "agent_id": "agent-alpha",
  "payload": {
    "type": "binary",
    "vote": "yes",
    "confidence": 0.85,
    "reason": "主要论点说服力强"
  }
}
```

`vote` 取值: `yes` | `no` | `abstain`

**排序选择投票**（ranked_choice / borda_count / instant_runoff）:
```json
{
  "type": "VOTE",
  "motion_id": "motion-abc",
  "payload": {
    "type": "ranking",
    "ranking": ["option_a", "option_b", "option_c"],
    "confidence": 0.7
  }
}
```

**批准投票**（approval）:
```json
{
  "type": "VOTE",
  "motion_id": "motion-abc",
  "payload": {
    "type": "approval",
    "approved": ["option_a", "option_c"],
    "confidence": 0.6
  }
}
```

**评分投票**（range）:
```json
{
  "type": "VOTE",
  "motion_id": "motion-abc",
  "payload": {
    "type": "range",
    "scores": {"option_a": 8.5, "option_b": 6.0, "option_c": 9.0},
    "confidence": 0.8
  }
}
```

#### PING — 心跳探测

```json
{"type": "PING"}
```

#### DEVILS_ADVOCATE_RESPONSE — 魔鬼代言人回应

```json
{
  "type": "DEVILS_ADVOCATE_RESPONSE",
  "motion_id": "motion-abc",
  "agent_id": "agent-beta",
  "payload": {
    "counter_argument": "微服务增加了运维复杂度...",
    "challenged_point": "隔离性优势"
  }
}
```

### 服务端→客户端消息

#### WELCOME — 注册确认

```json
{
  "type": "WELCOME",
  "agent_id": "agent-alpha",
  "payload": {"message": "Registration successful"}
}
```

#### PONG — 心跳回应

```json
{"type": "PONG"}
```

#### BROADCAST — 发言广播

```json
{
  "type": "BROADCAST",
  "motion_id": "motion-abc",
  "agent_id": "agent-alpha",
  "payload": {
    "round": 1,
    "stance": "support",
    "content": "微服务提供更好的隔离性...",
    "evidence": [...]
  }
}
```

#### REQUEST_VOTE — 请求投票

```json
{
  "type": "REQUEST_VOTE",
  "motion_id": "motion-abc",
  "payload": {
    "voting_method": "simple_majority",
    "forced": false
  }
}
```

#### VOTE_CONFIRMED — 投票确认

```json
{
  "type": "VOTE_CONFIRMED",
  "motion_id": "motion-abc",
  "payload": {"vote": "yes", "agent_id": "agent-alpha"}
}
```

#### RESULT — 讨论结果

```json
{
  "type": "RESULT",
  "motion_id": "motion-abc",
  "payload": {
    "counts": {"yes": 3, "no": 1, "abstain": 0},
    "decision": "adopted"
  }
}
```

#### NEW_MOTION — 新议题通知

```json
{
  "type": "NEW_MOTION",
  "motion_id": "motion-abc",
  "payload": {"title": "...", "status": "discussing"}
}
```

#### ERROR — 错误

```json
{
  "type": "ERROR",
  "payload": {
    "code": "cannot_speak",
    "message": "Not allowed to speak"
  }
}
```

#### AGENT_OFFLINE — Agent 离线通知

```json
{
  "type": "AGENT_OFFLINE",
  "agent_id": "agent-beta"
}
```

### 完整交互示例

```
1. Client → CONNECT  ws://localhost:8765/ws/agent-alpha
2. Client → {"type": "REGISTER", "agent_id": "agent-alpha", "payload": {...}}
3. Server → {"type": "WELCOME", "agent_id": "agent-alpha", "payload": {...}}

4. Server → {"type": "NEW_MOTION", "motion_id": "m1", "payload": {...}}

5. Client → {"type": "SPEAK", "motion_id": "m1", "agent_id": "agent-alpha", "payload": {"content": "我支持方案A", "stance": "support"}}
6. Server → {"type": "BROADCAST", "motion_id": "m1", "payload": {"delivered": true}}

7. Server → {"type": "REQUEST_VOTE", "motion_id": "m1", "payload": {"voting_method": "simple_majority"}}

8. Client → {"type": "VOTE", "motion_id": "m1", "agent_id": "agent-alpha", "payload": {"type": "binary", "vote": "yes", "confidence": 0.9}}
9. Server → {"type": "VOTE_CONFIRMED", "motion_id": "m1", "payload": {"vote": "yes"}}

10. Server → {"type": "RESULT", "motion_id": "m1", "payload": {"counts": {...}, "decision": "adopted"}}
```

### 错误码

| 错误码 | 说明 |
|--------|------|
| `missing_motion_id` | 请求中缺少 motion_id |
| `cannot_speak` | 当前状态不允许发言 |
| `cannot_vote` | 当前状态不允许投票或已投过票 |
| `not_found` | 议题不存在 |
| `invalid_vote_format` | 投票格式与投票方式不匹配 |
| `not_registered` | Agent 未注册 |

---

## Phase 8: 可观测性端点

### GET /metrics

Prometheus 格式指标暴露。

**响应**: `text/plain` — OpenMetrics/Prometheus 文本格式

---

### GET /events

获取事件历史。

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `since` | string | null | ISO 时间戳，返回此时间后的事件 |
| `type` | string | null | 过滤事件类型 |
| `limit` | int | 100 | 返回数量上限 |

**响应**: `EventResponse[]` 数组

---

### GET /events/stream

SSE 实时事件流。

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tenant_id` | string | null | 过滤租户 |

**响应**: `text/event-stream` — SSE 格式

---

### GET /discussions/{motion_id}/timeline

获取讨论时间线（发言 + 投票按时间排序）。

**响应**: `TimelineEntry[]` 数组

---

## Phase 8: 多租户端点

### POST /tenants

创建租户。

**请求体**:
```json
{
  "tenant_id": "team-alpha",
  "name": "Alpha Team",
  "config": {
    "max_agents": 10,
    "max_concurrent_discussions": 3
  }
}
```

**响应**: `Tenant` 对象

**状态码**:
- `200` — 创建成功
- `409` — 租户已存在

---

### GET /tenants

列出所有租户。

**响应**: `Tenant[]` 数组

---

### GET /tenants/{tenant_id}

获取租户详情。

**响应**: `Tenant` 对象

**状态码**:
- `200` — 成功
- `404` — 租户不存在

---

### DELETE /tenants/{tenant_id}

删除租户（软删除）。

**状态码**:
- `200` — 删除成功
- `404` — 租户不存在
- `403` — 不能删除 default 租户

---

## Phase 8: Dashboard

### GET /dashboard

Dashboard HTML 页面。

**响应**: `text/html`

---

### GET /static/{file}

Dashboard 静态资源。

---

## Phase 8: WebSocket 多租户

WebSocket 连接支持 `tenant_id` 参数实现租户隔离：

```
ws://host:8765/ws/{agent_id}?tenant_id=team-alpha
```

不带 `tenant_id` 时默认使用 `"default"` 租户（向后兼容）。
同一租户的 Agent 只能看到同租户的消息和事件。
