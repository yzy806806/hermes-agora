# Hermes Agora 🏛️

> Multi-Agent Deliberation Framework for Hermes

Hermes Agora 是一个让多个 Hermes Agent 进行结构化讨论、协商、投票决策的开源框架。

每个参与讨论的 Agent 都是一个完整的 Hermes 实例，自带记忆、技能、自我进化能力。讨论越多，团队越聪明。

## 核心理念

- **不是新 Agent 框架** — 复用 Hermes 生态，不造轮子
- **自建协调调度** — 独立 Coordinator 服务，不依赖 kanban
- **进化闭环** — 讨论经验自动沉淀，团队持续变聪明

## 架构

```
                    ┌─────────────────┐
                    │  Coordinator    │ ← 调度中心（独立服务）
                    │  (调度+存储)     │
                    └────────┬────────┘
                             │ HTTP + WebSocket
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ Hermes A│         │ Hermes B│         │ Hermes C│
   │ + Agent │         │ + Agent │         │ + Agent │
   │  Client │         │  Client │         │  Client │
   └─────────┘         └─────────┘         └─────────┘
```

## 组件

### Coordinator（调度中心）

独立服务，负责：
- 议题管理（创建、状态流转）
- 讨论流程控制（轮次、发言顺序）
- 消息广播（发给所有 participant）
- 投票统计
- 讨论历史存储（SQLite）
- 结果输出

### Agent Client（客户端库）

每个 Hermes 实例运行的客户端，负责：
- 向 Coordinator 注册
- 接收议题/消息
- 调用本地 Hermes（通过 CLI 或 API）
- 提交回复/投票
- 同步讨论历史到本地 memory

### Hermes 实例

标准 Hermes，复用：
- 🧠 memory — 记忆讨论经验
- 🛠 skills — 调用工具搜索、执行代码
- 🧬 curator — 自我进化，优化讨论策略

## 通信协议

```
Coordinator ←→ Agent Client: HTTP + WebSocket

消息类型：
- REGISTER     agent 注册
- NEW_MOTION   新议题
- SPEAK        发言
- VOTE         投票
- SYNC         同步历史
- RESULT       最终结果
```

## 讨论流程

```
1. 用户 → Coordinator: 创建议题
2. Coordinator → 所有 Agent: NEW_MOTION
3. Agent → 本地 Hermes: 思考（可调用工具）
4. Agent → Coordinator: SPEAK（观点）
5. Coordinator 广播给其他 Agent
6. 重复 3-5（N轮）
7. Coordinator → 所有 Agent: 请求投票
8. Agent → Coordinator: VOTE（立场+理由）
9. Coordinator 统计 → 输出结果
10. Agent → 本地 Hermes memory: 记录经验
```

## 自我进化闭环

```
讨论 → 结论写入 memory → curator 优化策略 → 下次讨论更聪明
```

- 哪些论点被采纳了？→ 强化
- 哪些判断错了？→ 纠正
- 哪些 skill 有用？→ 保留
- 讨论流程哪里卡了？→ 优化

## 技术栈

- **语言**: Python 3.11+
- **通信**: FastAPI + WebSocket
- **存储**: SQLite
- **Agent 接入**: Hermes CLI / Gateway API

## 项目状态

🚧 规划中 — 正在编写详细设计文档

## License

MIT
