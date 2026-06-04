# Hermes Agora Protocol Specification

Version: 0.1.0-draft

## 概述

本文档定义 Hermes Agora 的通信协议、消息格式、讨论流程。

## 术语

- **Coordinator**: 调度中心服务
- **Agent**: 参与讨论的 Hermes 实例（通过 Agent Client 接入）
- **Motion**: 议题，待讨论的问题/提案
- **Round**: 轮次，每轮所有 Agent 发言一次
- **Vote**: 投票，Agent 对议题的立场

## 通信层

### 传输协议

- **注册/控制**: HTTP REST API
- **实时消息**: WebSocket

### 端点

```
HTTP:
  POST /agents/register      Agent 注册
  POST /motions              创建议题
  GET  /motions/{id}         获取议题详情
  GET  /motions/{id}/history 获取讨论历史

WebSocket:
  /ws/{agent_id}             Agent 实时消息通道
```

## 消息格式

所有消息为 JSON，包含通用字段：

```json
{
  "type": "MESSAGE_TYPE",
  "motion_id": "uuid",
  "agent_id": "string",
  "timestamp": "ISO8601",
  "payload": { ... }
}
```

### 消息类型

#### REGISTER (Agent → Coordinator)

Agent 注册

```json
{
  "type": "REGISTER",
  "agent_id": "agent-alpha",
  "payload": {
    "name": "Alpha",
    "hermes_endpoint": "http://localhost:8080",
    "model": "mini-max",
    "capabilities": ["web_search", "code_execution"]
  }
}
```

#### NEW_MOTION (Coordinator → Agent)

新议题通知

```json
{
  "type": "NEW_MOTION",
  "motion_id": "uuid",
  "payload": {
    "title": "是否采用微服务架构",
    "description": "当前单体应用面临扩展问题...",
    "context": "背景材料、约束条件",
    "rounds": 3,
    "voting_method": "simple_majority"
  }
}
```

#### SPEAK (Agent → Coordinator)

发言

```json
{
  "type": "SPEAK",
  "motion_id": "uuid",
  "agent_id": "agent-alpha",
  "payload": {
    "round": 1,
    "stance": "support|oppose|neutral",
    "content": "我认为应该采用微服务，理由如下...",
    "evidence": [
      {"type": "web_search", "query": "microservices scalability"},
      {"type": "reference", "source": "past_experience"}
    ]
  }
}
```

#### BROADCAST (Coordinator → Agent)

广播其他 Agent 的发言

```json
{
  "type": "BROADCAST",
  "motion_id": "uuid",
  "payload": {
    "speaker_id": "agent-beta",
    "speaker_name": "Beta",
    "round": 1,
    "stance": "oppose",
    "content": "我反对，微服务会增加运维复杂度..."
  }
}
```

#### REQUEST_VOTE (Coordinator → Agent)

请求投票

```json
{
  "type": "REQUEST_VOTE",
  "motion_id": "uuid",
  "payload": {
    "summary": "讨论汇总：3轮讨论后，主要分歧点为..."
  }
}
```

#### VOTE (Agent → Coordinator)

投票

```json
{
  "type": "VOTE",
  "motion_id": "uuid",
  "agent_id": "agent-alpha",
  "payload": {
    "vote": "yes|no|abstain",
    "confidence": 0.8,
    "reason": "虽然运维复杂度增加，但扩展收益更大..."
  }
}
```

#### RESULT (Coordinator → Agent)

最终结果

```json
{
  "type": "RESULT",
  "motion_id": "uuid",
  "payload": {
    "decision": "adopted|rejected|no_consensus",
    "votes": {
      "yes": 2,
      "no": 1,
      "abstain": 0
    },
    "rationale": "多数支持，主要理由为...",
    "action_items": ["创建架构设计任务", "评估运维成本"]
  }
}
```

## 讨论流程状态机

```
[DRAFT] → [DISCUSSING] → [VOTING] → [CLOSED]
              ↓              ↓
           (轮次进行)     (等待投票)
```

### 状态转换

1. **DRAFT → DISCUSSING**: Coordinator 收到议题，广播给所有 Agent
2. **DISCUSSING → VOTING**: 所有轮次完成，请求投票
3. **VOTING → CLOSED**: 所有 Agent 已投票，输出结果

## Agent 行为规范

### 发言规则

1. 每轮发言一次，等待 Coordinator 广播其他 Agent 后再进入下一轮
2. 发言必须包含 `stance`（立场）
3. 可引用证据（搜索结果、过往经验）
4. 可质疑其他 Agent 的论点

### 投票规则

1. 必须在收到 `REQUEST_VOTE` 后投票
2. 投票必须附带理由
3. 可弃权（abstain）

### 进化行为

1. 收到 `RESULT` 后，将讨论经验写入本地 Hermes memory
2. 记录：自己的论点是否被采纳、判断是否正确
3. Curator 定期优化讨论策略

## 错误处理

```json
{
  "type": "ERROR",
  "payload": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent not registered"
  }
}
```

错误码：
- `AGENT_NOT_FOUND`: Agent 未注册
- `MOTION_NOT_FOUND`: 议题不存在
- `INVALID_STATE`: 状态不允许该操作
- `ROUND_NOT_COMPLETE`: 轮次未完成

## 扩展点

### 投票方法

- `simple_majority`: 简单多数
- `supermajority`: 超过 2/3
- `unanimous`: 全票通过
- `weighted`: 加权投票（根据 Agent 可信度）

### Agent 角色

- `moderator`: 主持人（可选，由 Coordinator 担任）
- `expert`: 专家（特定领域知识）
- `devil_advocate`: 魔鬼代言人（故意提出反对意见）
- `neutral`: 中立观察者

---

## 下一步

- [ ] 定义 SQLite 存储结构
- [ ] 实现 Coordinator 服务
- [ ] 实现 Agent Client 库
- [ ] 编写集成测试
