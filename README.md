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

### Coordinator Agent（主持人）

Coordinator 本身是一个 Hermes Agent，不只是消息中转，而是一个**有思想的主持人**：

- 🧠 **有记忆** — 记住历史讨论、决策模式、哪些论点被采纳
- 🛠 **有技能** — 能调用工具搜索、分析、总结
- 🧬 **能进化** — curator 优化调度策略（什么时候推进投票、什么时候追问）
- 💡 **能决策** — 判断讨论是否跑偏，发现共识点，主动引导

### Participant Agent（讨论者）

每个参与者也是完整的 Hermes 实例：

- 🧠 **有记忆** — 记住自己的判断是否正确，经验自动沉淀
- 🛠 **有技能** — 讨论中可以搜索、计算、执行代码
- 🧬 **能进化** — 讨论策略越来越好

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
| `/agora discuss <topic>` | 发起讨论 |
| `/agora vote <motion_id>` | 发起投票 |
| `/agora history <motion_id>` | 查看讨论历史 |

### 生命周期钩子（Hooks）

| 钩子 | 用途 |
|------|------|
| `on_session_start` | Agent 上线，向 Coordinator 注册 |
| `on_session_end` | 讨论经验写入 memory |
| `post_tool_call` | 记录讨论中的工具使用作为证据 |

## 讨论流程

```
1. 用户 → /agora discuss "是否采用微服务架构？"
2. Coordinator 收到议题 → 智能分析背景 → 广播给所有 Agent
3. 各 Agent 独立思考（可调用工具搜索、分析）
4. 各 Agent 通过 agora_speak 提交观点
5. Coordinator 智能判断：
   - 分歧大 → 追问关键点
   - 有共识 → 推进投票
   - 跑偏了 → 拉回正题
6. 重复 3-5（N轮）
7. Coordinator 发起投票
8. 各 Agent 通过 agora_vote 投票（立场+理由+置信度）
9. Coordinator 统计 → 宣布结果
10. 所有 Agent（包括 Coordinator）将经验写入 memory → 下次更聪明
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
  coordinator_url: "ws://10.0.0.25:8970"  # Coordinator Agent 的 WebSocket 地址
  agent_name: "Alpha"                       # 本 Agent 名称
  role: "participant"                       # participant | coordinator
  default_rounds: 3                         # 默认讨论轮次
  voting_method: "simple_majority"          # 投票方式
```

Coordinator Agent 的配置：

```yaml
agora:
  role: "coordinator"
  port: 8970
  default_rounds: 3
  voting_method: "simple_majority"
```

## 自举（Bootstrapping）

**用 Agora 来开发 Agora。**

等插件基本可用，就让 AI 团队通过 Agora 讨论 Agora 自身的开发方向：
- 下一步该做什么功能？→ 讨论优先级
- 技术方案选 A 还是 B？→ 讨论优劣
- 发现设计问题？→ 讨论改进方案

用户最终拍板，但日常方案论证交给 AI 团队自决。
项目越成熟，团队讨论质量越高，开发越自主。

## 项目状态

🚧 开发中

## License

MIT
