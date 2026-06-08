# Hermes Agora 🏛️

> Multi-Agent Deliberation Plugin for Hermes

Hermes Agora 是一个 Hermes 插件，让多个 Hermes Agent 进行结构化讨论、协商、投票决策。

每个参与讨论的 Agent 都是一个完整的 Hermes 实例，自带记忆、技能、自我进化能力。讨论越多，团队越聪明。

## 核心理念

- **Hermes 原生插件** — 复用 Hermes 的 memory、skills、curator，不造轮子
- **Coordinator 也是 Agent** — 调度中心不是死板的消息中转，而是一个有思想的主持人
- **自建协调调度** — 不依赖 kanban，通过 Agora 协议通信
- **进化闭环** — 讨论经验自动沉淀，团队持续变聪明

## 架构

```
                    ┌──────────────────────┐
                    │  Coordinator Agent   │ ← 也是一个 Hermes 实例
                    │  (调度+存储+智能引导)  │    有 memory/skills/curator
                    └──────────┬───────────┘
                               │ WebSocket
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Hermes A│           │ Hermes B│           │ Hermes C│
   │ + Agora │           │ + Agora │           │ + Agora │
   │  Client │           │  Client │           │  Client │
   └─────────┘           └─────────┘           └─────────┘
```

## 特性

### Phase 1: MVP 基础
- REST API 创建/查询议题
- WebSocket 实时发言+投票
- 讨论状态机（draft → discussing → voting → closed）
- SQLite 持久化存储

### Phase 2: 智能讨论
- 实时讨论评估（共识度、分歧点检测）
- 共识提前判断（跳过剩余轮次直接投票）
- 魔鬼代言人（自动生成反对观点）
- 分歧点聚焦（引导讨论关键分歧）
- 动态轮次调整（根据讨论质量增减轮次）
- 9 种投票方式（简单多数、排序选择、批准、评分等）

### Phase 3: 记忆进化
- 讨论经验自动沉淀到 memory
- 策略优化（curator 分析历史，优化调度）
- 历史模式分析（识别重复讨论模式）
- 相似议题检索（避免重复讨论）
- 判断追踪（记录每个 Agent 的判断正确率）

### Phase 4: 自举系统
- Agora 讨论 Agora 自身开发方向
- 触发器管理（定时/事件/手动触发）
- 议题自动生成
- 审批流程（AI 提议 → 人类审批）

### Phase 5: 容错安全
- 心跳监控（检测 Agent 离线）
- 超时管理（轮次/投票/讨论级别超时）
- 死锁预防（检测循环引用并注入中断信号）
- 输入验证 + 清洗（防注入、长度限制）
- 速率限制（防止单 Agent 消息洪泛）

### Phase 6: 质量增强
- 质量守卫（5 项检查：论据充分性、逻辑一致性等）
- 质量评分（量化讨论质量）
- 视角保障（确保多角度观点被表达）
- 讨论角色分配（支持/反对/专家/中立等）
- 多模型差异利用（不同模型扮演不同角色）

## 作为 Hermes 插件提供

### 工具（Tools）

| 工具 | 说明 |
|------|------|
| `agora_create_motion` | 创建讨论议题 |
| `agora_speak` | 发言（观点+立场+证据） |
| `agora_vote` | 投票（赞成/反对/弃权+理由） |
| `agora_list_motions` | 查看议题列表 |
| `agora_get_history` | 获取讨论历史 |
| `agora_get_result` | 获取讨论结果 |

### 斜杠命令（Slash Commands）

| 命令 | 说明 |
|------|------|
| `/agora` | Agora 状态总览 |
| `/agora new <topic>` | 发起讨论 |
| `/agora list` | 查看议题列表 |
| `/agora status <id>` | 查看议题状态 |
| `/agora vote <id>` | 发起投票 |
| `/agora result <id>` | 查看讨论结果 |

### 生命周期钩子（Hooks）

| 钩子 | 用途 |
|------|------|
| `on_session_start` | Agent 上线，向 Coordinator 注册 |
| `on_session_end` | 讨论经验写入 memory |
| `post_tool_call` | 记录讨论中的工具使用作为证据 |

## 安装

```bash
# 从 GitHub 安装
hermes plugins install yzy806806/hermes-agora --enable

# 或本地开发
hermes plugins install /path/to/hermes-agora --enable
```

## 配置

在 `~/.hermes/config.yaml` 中：

### Participant Agent 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `agora.coordinator_url` | `http://localhost:8765` | Coordinator 地址 |
| `agora.agent_id` | 空 | 本 Agent ID（留空自动生成） |
| `agora.agent_name` | `AgoraAgent` | Agent 显示名称 |
| `agora.default_rounds` | `3` | 默认讨论轮次 |
| `agora.default_voting_method` | `simple_majority` | 默认投票方式 |
| `agora.connect_timeout` | `10` | 连接超时（秒） |
| `agora.request_timeout` | `30` | 请求超时（秒） |
| `agora.max_retry` | `3` | 最大重试次数 |

### Coordinator Agent 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| `host` | `AGORA_HOST` | `0.0.0.0` | 监听地址 |
| `port` | `AGORA_PORT` | `8765` | 监听端口 |
| `db_path` | `AGORA_DB_PATH` | `data/agora.db` | 数据库路径 |
| `debug` | `AGORA_DEBUG` | `false` | 调试模式 |
| `default_rounds` | `AGORA_DEFAULT_ROUNDS` | `3` | 默认讨论轮次 |
| `default_voting_method` | `AGORA_DEFAULT_VOTING_METHOD` | `simple_majority` | 默认投票方式 |
| `smart_discussion_enabled` | `AGORA_SMART_DISCUSSION_ENABLED` | `true` | 启用智能讨论 |
| `devils_advocate_enabled` | `AGORA_DEVILS_ADVOCATE_ENABLED` | `true` | 启用魔鬼代言人 |
| `heartbeat_interval_seconds` | `AGORA_HEARTBEAT_INTERVAL_SECONDS` | `30` | 心跳间隔 |
| `round_timeout_seconds` | `AGORA_ROUND_TIMEOUT_SECONDS` | `300` | 轮次超时 |
| `vote_timeout_seconds` | `AGORA_VOTE_TIMEOUT_SECONDS` | `120` | 投票超时 |
| `discussion_timeout_seconds` | `AGORA_DISCUSSION_TIMEOUT_SECONDS` | `1800` | 讨论总超时 |

## Docker 部署

### 生产部署

```bash
# 构建并启动 Coordinator
docker compose -f docker-compose.prod.yaml up -d

# 查看日志
docker compose -f docker-compose.prod.yaml logs -f
```

Coordinator 默认监听 `0.0.0.0:8765`，数据持久化到 Docker volume `agora-data`。

### 运行测试

```bash
# 单元测试
docker compose -f docker-compose.test.yaml run --rm tests

# 或本地运行
uv run pytest tests/ -m "not integration" -x -q
```

## 讨论流程

```
1. 用户 → /agora new "是否采用微服务架构？"
2. Coordinator 收到议题 → 智能分析背景 → 广播给所有 Agent
3. 各 Agent 独立思考（可调用工具搜索、分析）
4. 各 Agent 通过 agora_speak 提交观点
5. Coordinator 智能判断：
   - 分歧大 → 追问关键点 / 魔鬼代言人
   - 有共识 → 推进投票（共识提前判断）
   - 跑偏了 → 拉回正题（分歧点聚焦）
6. 重复 3-5（动态轮次，最多 N 轮）
7. Coordinator 发起投票
8. 各 Agent 通过 agora_vote 投票
9. Coordinator 统计 → 宣布结果
10. 所有 Agent 将经验写入 memory → 下次更聪明
```

## 自我进化闭环

```
讨论 → 结论写入 memory → curator 优化策略 → 下次讨论更聪明
```

**Coordinator 进化**：
- 学会什么时候该推进投票（别拖太久）
- 学会识别跑偏讨论（拉回正题）
- 记住哪些 Agent 擅长什么领域（优化发言顺序）

**Participant 进化**：
- 记住自己的判断是否正确
- 沉淀有效的论证模式
- 优化证据收集策略

## 自举（Bootstrapping）

**用 Agora 来开发 Agora。** AI 团队通过 Agora 讨论 Agora 自身的开发方向：
- 下一步该做什么功能？→ 讨论优先级
- 技术方案选 A 还是 B？→ 讨论优劣
- 发现设计问题？→ 讨论改进方案

用户最终拍板，但日常方案论证交给 AI 团队自决。

## 项目状态

📦 v0.7.0 — 生产可用（集成测试 + Docker 部署 + 文档完善）

## License

MIT
