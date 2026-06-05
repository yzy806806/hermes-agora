# Phase 1: 6 个基础工具设计

## 概述

本文档定义 Phase 1 中 6 个 Hermes Agora 工具的完整接口规范和实现逻辑。

## 架构概览

```
┌─────────────────┐         HTTP/WebSocket          ┌─────────────────┐
│  Hermes Agent   │ ◄─────────────────────────────► │   Coordinator   │
│  (Participant)  │                                │    (FastAPI)    │
│                 │                                │                 │
│ agora_* tools  │                                │  REST API       │
│    ↕ 调用        │                                │  WebSocket      │
└─────────────────┘                                │  SQLite Storage │
                                                   └─────────────────┘
```

- **HTTP API**: 创建 motion、查询列表/历史/结果
- **WebSocket**: 实时发言、投票、接收广播

## 前置条件

1. Coordinator 服务运行于 `http://localhost:8765`（可配置）
2. Agent 通过 WebSocket 连接 `ws://localhost:8765/ws/{agent_id}`
3. Agent 启动时自动注册到 Coordinator

---

## 工具 1: agora_create_motion

### 功能
发起一个新的讨论议程（Motion）

### 接口定义

```python
async def agora_create_motion(
    title: str,                          # 议程标题（必填）
    description: str = "",               # 议程描述/背景
    context: str | None = None,          # 额外上下文信息
    rounds: int | None = None,           # 讨论轮次（默认3）
    voting_method: str = "simple_majority",  # 投票方法
) -> dict:
```

### 输入验证
| 参数 | 类型 | 必填 | 约束 |
|------|------|------|------|
| title | str | 是 | 1-200 字符 |
| description | str | 否 | 最大 5000 字符 |
| context | str | 否 | 最大 2000 字符 |
| rounds | int | 否 | 1-10，默认 3 |
| voting_method | str | 否 | 枚举值见下文 |

### voting_method 枚举
- `simple_majority` - 简单多数（超过 50%）
- `supermajority` - 绝对多数（超过 2/3）
- `unanimous` - 全票通过

### 输出格式

```python
{
    "status": "success",           # "success" | "error"
    "motion_id": "uuid-string",    # 议程唯一 ID
    "title": "xxx",
    "description": "xxx",
    "rounds": 3,
    "voting_method": "simple_majority",
    "status": "draft",             # 当前状态
    "created_at": "2026-06-05T12:00:00Z",
    "message": "Motion created successfully"
}
```

### 实现逻辑

1. **本地检查**：验证必填参数
2. **调用 Coordinator HTTP API**：
   ```
   POST /api/v1/motions
   Content-Type: application/json
   
   {
     "title": "xxx",
     "description": "xxx",
     "context": "xxx",
     "rounds": 3,
     "voting_method": "simple_majority"
   }
   ```
3. **返回结果**：解析响应，封装为工具输出格式
4. **错误处理**：
   - 网络错误 → `status: "error"`, `message: "Connection failed"`
   - 参数错误 → `status: "error"`, `message: "Invalid title"`
   - Coordinator 返回错误 → 透传错误信息

---

## 工具 2: agora_speak

### 功能
在讨论中发表意见/发言

### 接口定义

```python
async def agora_speak(
    motion_id: str,                     # 议程 ID（必填）
    content: str,                       # 发言内容（必填）
    stance: str = "neutral",            # 立场：support | oppose | neutral
    evidence: list[dict] | None = None, # 证据/引用列表
) -> dict:
```

### 输入验证
| 参数 | 类型 | 必填 | 约束 |
|------|------|------|------|
| motion_id | str | 是 | 有效的 UUID 格式 |
| content | str | 是 | 1-5000 字符 |
| stance | str | 否 | support/oppose/neutral，默认 neutral |
| evidence | list | 否 | 最大 10 项，每项需含 type 和 content |

### evidence 格式
```python
[
    {"type": "url", "content": "https://..."},
    {"type": "file", "content": "/path/to/file"},
    {"type": "data", "content": "引用数据..."}
]
```

### 输出格式

```python
{
    "status": "success",
    "message_id": "msg-uuid-string",
    "motion_id": "motion-uuid-string",
    "agent_id": "agent-xxx",
    "content": "xxx",
    "stance": "support",
    "round": 1,
    "timestamp": "2026-06-05T12:05:00Z",
    "message": "Speech submitted"
}
```

### 实现逻辑

1. **状态检查**：通过 HTTP GET `/api/v1/motions/{motion_id}` 获取议程状态
2. **权限校验**：确认议程状态为 `discussing`
3. **发送 WebSocket 消息**：
   ```json
   {
     "type": "SPEAK",
     "motion_id": "xxx",
     "agent_id": "agent-xxx",
     "payload": {
       "content": "xxx",
       "stance": "support",
       "evidence": [...]
     }
   }
   ```
4. **等待确认**：Coordinator 广播 `BROADCAST` 消息确认收到
5. **返回结果**：成功返回 message_id，失败返回错误信息

### 边界情况

| 场景 | 处理 |
|------|------|
| 议程不存在 | 返回 error: "Motion not found" |
| 议程不在讨论状态 | 返回 error: "Motion is not in discussing status" |
| 已在当前轮次发言 | 返回 error: "Already spoke in this round" |
| WebSocket 未连接 | 自动重连（3次），失败则返回 error |
| 发言超时（120s） | 返回 error: "Speech timeout" |

---

## 工具 3: agora_vote

### 功能
对议程进行投票

### 接口定义

```python
async def agora_vote(
    motion_id: str,           # 议程 ID（必填）
    vote: str,                # 投票：yes | no | abstain
    reason: str = "",         # 投票理由
    confidence: float = 0.5,  # 置信度 0.0-1.0
) -> dict:
```

### 输入验证
| 参数 | 类型 | 必填 | 约束 |
|------|------|------|------|
| motion_id | str | 是 | 有效的 UUID 格式 |
| vote | str | 是 | yes / no / abstain |
| reason | str | 否 | 最大 1000 字符 |
| confidence | float | 否 | 0.0-1.0，默认 0.5 |

### 输出格式

```python
{
    "status": "success",
    "vote_id": "vote-uuid-string",
    "motion_id": "motion-uuid-string",
    "agent_id": "agent-xxx",
    "vote": "yes",
    "reason": "xxx",
    "confidence": 0.8,
    "timestamp": "2026-06-05T12:10:00Z",
    "message": "Vote submitted"
}
```

### 实现逻辑

1. **状态检查**：确认议程状态为 `voting`
2. **检查是否已投票**：GET `/api/v1/motions/{motion_id}/votes` 确认未投票
3. **发送 WebSocket 消息**：
   ```json
   {
     "type": "VOTE",
     "motion_id": "xxx",
     "agent_id": "agent-xxx",
     "payload": {
       "vote": "yes",
       "reason": "xxx",
       "confidence": 0.8
     }
   }
   ```
4. **返回结果**

### 边界情况

| 场景 | 处理 |
|------|------|
| 议程不在投票状态 | 返回 error: "Motion is not open for voting" |
| 已投过票 | 返回 error: "Already voted on this motion" |
| 投票超时（60s） | 返回 error: "Voting timeout" |

---

## 工具 4: agora_list_motions

### 功能
列出议程列表

### 接口定义

```python
async def agora_list_motions(
    status: str | None = None,  # 状态过滤：draft | discussing | voting | closed
    limit: int = 10,            # 返回数量限制
    offset: int = 0,            # 偏移量（分页）
) -> dict:
```

### 输入验证
| 参数 | 类型 | 必填 | 约束 |
|------|------|------|------|
| status | str | 否 | draft/discussing/voting/closed |
| limit | int | 否 | 1-100，默认 10 |
| offset | int | 否 | >= 0，默认 0 |

### 输出格式

```python
{
    "status": "success",
    "motions": [
        {
            "motion_id": "uuid-string",
            "title": "xxx",
            "description": "xxx",
            "status": "discussing",
            "current_round": 1,
            "rounds": 3,
            "voting_method": "simple_majority",
            "created_at": "2026-06-05T12:00:00Z",
            "participants": 3
        },
        ...
    ],
    "total": 15,
    "limit": 10,
    "offset": 0,
    "message": "Retrieved 10 motions"
}
```

### 实现逻辑

直接调用 Coordinator HTTP API：
```
GET /api/v1/motions?status=discussing&limit=10&offset=0
```

---

## 工具 5: agora_get_history

### 功能
获取议程的讨论历史（发言记录 + 投票记录）

### 接口定义

```python
async def agora_get_history(
    motion_id: str,       # 议程 ID
    limit: int = 50,      # 消息数量限制
    include_votes: bool = True,  # 是否包含投票记录
) -> dict:
```

### 输入验证
| 参数 | 类型 | 必填 | 约束 |
|------|------|------|------|
| motion_id | str | 是 | 有效 UUID |
| limit | int | 否 | 1-200，默认 50 |
| include_votes | bool | 否 | 默认 true |

### 输出格式

```python
{
    "status": "success",
    "motion_id": "uuid-string",
    "motion_title": "xxx",
    "messages": [
        {
            "message_id": "msg-xxx",
            "agent_id": "agent-xxx",
            "agent_name": "Agent Alpha",
            "content": "xxx",
            "stance": "support",
            "round": 1,
            "timestamp": "2026-06-05T12:05:00Z",
            "evidence": [...]
        },
        ...
    ],
    "votes": [
        {
            "vote_id": "vote-xxx",
            "agent_id": "agent-xxx",
            "agent_name": "Agent Alpha",
            "vote": "yes",
            "reason": "xxx",
            "confidence": 0.8,
            "timestamp": "2026-06-05T12:10:00Z"
        },
        ...
    ],
    "message": "Retrieved history"
}
```

### 实现逻辑

调用 Coordinator HTTP API：
```
GET /api/v1/motions/{motion_id}/history?limit=50&include_votes=true
```

---

## 工具 6: agora_get_result

### 功能
获取议程的最终投票结果

### 接口定义

```python
async def agora_get_result(
    motion_id: str,   # 议程 ID
) -> dict:
```

### 输入验证
| 参数 | 类型 | 必填 | 约束 |
|------|------|------|------|
| motion_id | str | 是 | 有效 UUID |

### 输出格式

```python
{
    "status": "success",
    "motion_id": "uuid-string",
    "motion_title": "xxx",
    "decision": "approved",        # approved | rejected | no_consensus
    "voting_method": "simple_majority",
    "votes_summary": {
        "yes": 3,
        "no": 1,
        "abstain": 1,
        "total": 5
    },
    "votes": [...],  # 详细投票记录
    "result_details": {
        "threshold": 3,  # 获胜所需票数
        "passed": true,
        "margin": 2      # 胜出票数差
    },
    "closed_at": "2026-06-05T12:15:00Z",
    "message": "Motion closed with approval"
}
```

### 实现逻辑

1. 获取议程状态，确认已关闭
2. 调用 Coordinator HTTP API：
   ```
   GET /api/v1/motions/{motion_id}/result
   ```
3. 计算投票结果（根据 voting_method）

### 边界情况

| 场景 | 处理 |
|------|------|
| 议程未关闭 | 返回 error: "Motion is not closed yet" |
| 议程不存在 | 返回 error: "Motion not found" |

---

## 配置管理

工具从 Hermes 配置中读取 Coordinator 连接信息：

```yaml
# ~/.hermes/config.yaml
agora:
  coordinator_url: "http://localhost:8765"
  ws_protocol: "ws"
  agent_id: "agent-xxx"        # 自动生成或配置
  agent_name: "Agora Agent"    # 显示名称
  default_rounds: 3
  default_voting_method: "simple_majority"
  connect_timeout: 10          # 秒
  request_timeout: 30          # 秒
  max_retry: 3
```

---

## 错误响应格式

所有工具遵循统一的错误格式：

```python
{
    "status": "error",
    "error_code": "MOTION_NOT_FOUND",  # 错误码
    "message": "详细错误信息",
    "details": {}  # 额外调试信息（可选）
}
```

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| MOTION_NOT_FOUND | 议程不存在 |
| INVALID_STATUS | 状态不合法 |
| ALREADY_VOTED | 已投票 |
| ALREADY_SPEAK | 本轮已发言 |
| CONNECTION_FAILED | 连接 Coordinator 失败 |
| TIMEOUT | 操作超时 |
| INVALID_PARAMS | 参数验证失败 |

---

## 实现文件结构

```
hermes-agora/
├── __init__.py              # 工具实现（修改）
├── coordinator/
│   ├── __init__.py
│   ├── main.py              # FastAPI 服务
│   ├── config.py
│   ├── models.py
│   ├── router.py
│   ├── ws.py
│   ├── state.py
│   └── storage.py
└── docs/
    └── DESIGN-tools.md       # 本文档
```

---

## 下一步

1. **dev-merger 实现**：根据本设计文档实现 `__init__.py` 中的 6 个工具
2. **测试**：验证工具能正确调用 Coordinator
3. **集成测试**：完整流程测试（创建议程 → 讨论 → 投票 → 结果）