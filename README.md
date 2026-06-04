# Hermes Agora 🏛️

> Multi-Agent Deliberation Plugin for Hermes

Hermes Agora 是一个 Hermes 插件，让多个 Hermes Agent 进行结构化讨论、协商、投票决策。

每个参与讨论的 Agent 都是一个完整的 Hermes 实例，自带记忆、技能、自我进化能力。讨论越多，团队越聪明。

## 核心理念

- **Hermes 原生插件** — 复用 Hermes 的 memory、skills、curator，不造轮子
- **自建协调调度** — 独立 Coordinator 服务，不依赖 kanban
- **进化闭环** — 讨论经验自动沉淀，团队持续变聪明

## 架构

```
                    ┌─────────────────┐
                    │  Coordinator    │ ← 调度中心（插件内嵌服务）
                    │  (调度+存储)     │
                    └────────┬────────┘
                             │ HTTP + WebSocket
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ Hermes A│         │ Hermes B│         │ Hermes C│
   │ + Agora │         │ + Agora │         │ + Agora │
   │  Client │         │  Client │         │  Client │
   └─────────┘         └─────────┘         └─────────┘
```

## 组件

### Coordinator（调度中心）

插件内嵌的 FastAPI + WebSocket 服务，负责：
- 议题管理（创建、状态流转）
- 讨论流程控制（轮次、发言顺序）
- 消息广播（发给所有 participant）
- 投票统计
- 讨论历史存储（SQLite）
- 结果输出

### Agent Client（客户端）

插件提供的工具，每个 Hermes 实例安装后自动获得：
- 向 Coordinator 注册
- 接收议题/消息
- 提交回复/投票
- 同步讨论历史到本地 memory

### Hermes 实例

标准 Hermes，复用：
- memory（记忆讨论经验）
- skills（调用工具）
- curator（自我进化）

## 作为 Hermes 插件提供

### 工具（Tools）

| 工具 | 说明 |
|------|------|
| `agora_create_motion` | 创建讨论议题 |
| `agora_speak` | 发言 |
| `agora_vote` | 投票 |
| `agora_list_motions` | 查看议题列表 |
| `agora_get_history` | 获取讨论历史 |
| `agora_get_result` | 获取讨论结果 |

### 斜杠命令（Slash Commands）

| 命令 | 说明 |
|------|------|
| `/agora` | Agora 状态总览 |
| `/agora discuss <topic>` | 发起讨论 |
| `/agora vote <motion_id>` | 发起投票 |
| `/agora history <motion_id>` | 查看讨论历史 |

### 生命周期钩子（Hooks）

| 钩子 | 用途 |
|------|------|
| `on_session_start` | Agent 上线，向 Coordinator 注册 |
| `on_session_end` | 讨论经验写入 memory |
| `post_tool_call` | 记录讨论中的工具使用 |

## 讨论协议

### 消息格式

所有消息为 JSON：

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

| 类型 | 方向 | 说明 |
|------|------|------|
| `REGISTER` | Agent → Coordinator | Agent 注册 |
| `NEW_MOTION` | Coordinator → Agent | 新议题通知 |
| `SPEAK` | Agent → Coordinator | 发言 |
| `BROADCAST` | Coordinator → Agent | 广播其他 Agent 的发言 |
| `REQUEST_VOTE` | Coordinator → Agent | 请求投票 |
| `VOTE` | Agent → Coordinator | 投票 |
| `RESULT` | Coordinator → Agent | 最终结果 |

### 讨论流程

```
1. 用户 → /agora discuss "是否采用微服务架构？"
2. Coordinator 广播议题给所有 Agent
3. 各 Agent 独立思考（可调用工具搜索、分析）
4. 各 Agent 通过 agora_speak 提交观点
5. Coordinator 广播给其他 Agent
6. 重复 3-5（N轮）
7. 用户 → /agora vote <motion_id>
8. 各 Agent 通过 agora_vote 投票（立场+理由）
9. Coordinator 统计 → 输出结果
10. 各 Agent 将经验写入 memory → 下次更聪明
```

### 状态机

```
[DRAFT] → [DISCUSSING] → [VOTING] → [CLOSED]
```

## 自我进化闭环

```
讨论 → 结论写入 memory → curator 优化策略 → 下次讨论更聪明
```

- 哪些论点被采纳了？→ 强化
- 哪些判断错了？→ 纠正
- 哪些 skill 有用？→ 保留
- 讨论流程哪里卡了？→ 优化

## 项目结构

```
hermes-agora/
├── __init__.py              # 插件注册入口
├── plugin.yaml              # 插件清单
├── config.py                # 配置读取
├── tools.py                 # 工具定义和处理器
├── coordinator/             # 调度中心服务
│   ├── __init__.py
│   ├── app.py               # FastAPI 应用
│   ├── router.py            # REST API 路由
│   ├── ws.py                # WebSocket 处理
│   ├── state.py             # 讨论状态机
│   ├── storage.py           # SQLite 存储
│   └── models.py            # 数据模型
├── client/                  # Agent 客户端
│   ├── __init__.py
│   ├── ws_client.py         # WebSocket 客户端
│   └── memory_sync.py       # 讨论经验写入 memory
├── tests/
│   ├── test_coordinator.py
│   ├── test_tools.py
│   └── test_integration.py
├── docs/
│   ├── PROTOCOL.md          # 通信协议详细规范
│   └── ARCHITECTURE.md      # 架构设计文档
├── pyproject.toml
└── LICENSE
```

## 安装

```bash
# 从 GitHub 安装
hermes plugins install yzy806806/hermes-agora --enable

# 或本地开发
hermes plugins install /path/to/hermes-agora --enable
```

## 配置

在 `~/.hermes/config.yaml` 中：

```yaml
agora:
  coordinator_url: "http://localhost:8970"
  agent_name: "Alpha"
  default_rounds: 3
  voting_method: "simple_majority"
```

## 项目状态

🚧 开发中

## License

MIT
