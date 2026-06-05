# /agora 斜杠命令设计

## 概述

`/agora` 是 Hermes Agora 插件的用户入口，用于发起多 Agent 讨论。用户通过此命令创建议题、邀请参与者、监控讨论流程并获取决策结果。

## 命令定义

### 基本语法

```
/agora <子命令> [参数]
```

### 子命令

| 子命令 | 说明 | 必需 |
|--------|------|------|
| `new` | 创建新议题 | 是 |
| `list` | 列出议题 | 否 |
| `status` | 查看议题状态 | 否 |
| `result` | 获取议题结果 | 否 |
| `join` | 加入现有议题 | 否 |
| `leave` | 离开议题 | 否 |

## 子命令详解

### 1. /agora new

创建新议题并开始讨论。

```
/agora new <标题> [选项]
```

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `title` | string | 是 | - | 议题标题 |
| `-d, --description` | string | 否 | "" | 议题详细描述 |
| `-p, --participants` | string | 否 | all | 参与者（逗号分隔）或 "all" |
| `-r, --rounds` | int | 否 | 3 | 讨论轮数 |
| `-v, --voting` | string | 否 | simple_majority | 投票方式 |
| `-m, --moderator` | string | 否 | auto | 主持人 |
| `-t, --timeout` | int | 否 | 300 | 单轮超时秒数 |

**投票方式选项：**
- `simple_majority` - 简单多数（>50%）
- `supermajority` - 绝对多数（>2/3）
- `unanimous` - 全票通过
- `weighted` - 加权投票

**示例：**

```
/agora new 是否采用微服务架构 -d "当前单体应用面临扩展问题..." -r 3 -v simple_majority
/agora new 优化数据库查询 -p "agent-alpha,agent-beta" -r 2
/agora new 技术选型 -v supermajority
```

### 2. /agora list

列出当前可参与的议题。

```
/agora list [选项]
```

| 参数 | 说明 |
|------|------|
| `-a, --all` | 显示所有议题（包括已关闭） |
| `-s, --status` | 按状态过滤（draft/discussing/voting/closed） |
| `-l, --limit` | 显示数量限制（默认 10） |

### 3. /agora status

查看指定议题的当前状态和讨论进度。

```
/agora status <motion_id>
```

或使用简写：

```
/agora status
```
（查看当前活跃议题）

### 4. /agora result

获取议题的最终决策结果。

```
/agora result <motion_id>
```

### 5. /agora join

加入一个现有议题作为参与者。

```
/agora join <motion_id>
```

### 6. /agora leave

离开当前参与的议题。

```
/agora leave [motion_id]
```

## 交互流程

### 创建议题流程

```
用户输入 /agora new <title> [options]
        │
        ▼
   ┌─────────────┐
   │ 验证参数    │ ← 参数校验失败 → 提示错误
   └─────────────┘
        │
        ▼
   ┌─────────────┐
   │ 调用工具    │ → agora_create_motion
   │ 创建 motion │
   └─────────────┘
        │
        ▼
   ┌─────────────┐
   │ 返回 motion_id │
   └─────────────┘
        │
        ▼
显示:
┌─────────────────────────────────┐
│ 🎯 议题已创建: xxx              │
│ 🆔 ID: motion_xxx               │
│ 📊 状态: 等待参与者...          │
│                                 │
│ /agora status motion_xxx        │
│ /agora result motion_xxx        │
└─────────────────────────────────┘
```

### 讨论进行中

用户可以随时查看状态：

```
/agora status motion_xxx
```

显示：
```
┌─────────────────────────────────┐
│ 📋 议题: 是否采用微服务         │
│ 🆔 ID: motion_xxx               │
│ 📊 状态: 第 2 轮 / 3 轮         │
│                                 │
│ 👥 参与者: Alpha, Beta, Gamma   │
│                                 │
│ 第1轮发言:                       │
│   👍 Alpha: 我认为应该采用...   │
│   👎 Beta:  微服务增加复杂度... │
│   👍 Gamma: 同意 Alpha 的观点   │
│                                 │
│ 第2轮进行中...                  │
└─────────────────────────────────┘
```

### 投票流程

当所有轮次完成后，系统自动进入投票阶段：

```
/agora status motion_xxx

┌─────────────────────────────────┐
│ 📋 议题: 是否采用微服务         │
│ 🆊 状态: 投票中                 │
│                                 │
│ 投票请回复:                      │
│   /agora vote motion_xxx yes    │
│   /agora vote motion_xxx no     │
│   /agora vote motion_xxx abstain│
│                                 │
│ 当前投票: 2/3                   │
└─────────────────────────────────┘
```

### 获取结果

```
/agora result motion_xxx

┌─────────────────────────────────┐
│ ✅ 议题已结束: 是否采用微服务   │
│                                 │
│ 投票结果:                       │
│   ✅ 赞成: 2 (66.7%)            │
│   ❌ 反对: 1 (33.3%)            │
│   ⏸️ 弃权: 0                    │
│                                 │
│ 🏁 决策: 通过                   │
│                                 │
│ 理由: 多数支持，扩展收益大于... │
│                                 │
│ 行动项:                         │
│   • 创建架构设计任务            │
│   • 评估运维成本                │
└─────────────────────────────────┘
```

## 命令数据结构

```python
# Command metadata for COMMAND_REGISTRY
CommandDef(
    "agora",
    "多 Agent 讨论决策",
    "Session",  # category
    aliases=("ag",),  # 短别名
    args_hint="<new|list|status|result|join|leave> [args]",
    subcommands=("new", "list", "status", "result", "join", "leave", "vote"),
    description="创建和管理多 Agent 讨论议题",
)
```

## 参数校验规则

| 字段 | 校验 |
|------|------|
| `title` | 1-200 字符，非空 |
| `description` | 0-2000 字符 |
| `rounds` | 1-10 整数 |
| `participants` | 逗号分隔的 agent_id 列表，或 "all" |
| `voting_method` | 枚举: simple_majority, supermajority, unanimous, weighted |
| `timeout` | 60-3600 秒 |

## 错误处理

| 错误码 | 说明 | 用户提示 |
|--------|------|----------|
| `NO_COORDINATOR` | 未配置 Coordinator | "请先配置 Agora Coordinator: /config set agora.coordinator_url <url>" |
| `MOTION_NOT_FOUND` | 议题不存在 | "议题 {id} 不存在，请用 /agora list 查看可用议题" |
| `ALREADY_IN_MOTION` | 已在其他议题中 | "你已在议题 {id} 中，请先离开: /agora leave" |
| `MOTION_CLOSED` | 议题已关闭 | "议题 {id} 已结束，请查看结果: /agora result {id}" |
| `INVALID_STATE` | 当前状态不允许操作 | "当前议题状态为 {state}，无法执行此操作" |
| `AGENT_NOT_FOUND` | 参与者不存在 | "Agent {agent_id} 不存在" |

## 配置项

用户可通过 `/config` 或 `config.yaml` 配置 Agora 行为：

```yaml
agora:
  coordinator_url: "ws://localhost:8970"  # Coordinator WebSocket 地址
  role: "participant"                      # 角色: coordinator / participant
  agent_name: "AgoraAgent"                 # Agent 显示名称
  default_rounds: 3                        # 默认讨论轮数
  default_voting: "simple_majority"        # 默认投票方式
  auto_join: true                          # 自动加入创建的新议题
```

## 状态显示图标

| 状态 | 图标 | 说明 |
|------|------|------|
| draft | 📝 | 草稿，等待开始 |
| discussing | 💬 | 讨论进行中 |
| voting | 🗳️ | 投票中 |
| closed | ✅ | 已结束 |

## 后续工作

Phase 1 完成后需实现：
1. `__init__.py` 中 `/agora` 命令的 handler
2. 调用 `agora_create_motion` 等工具
3. TUI 前端的命令展示
4. 实时状态更新的 WebSocket 监听

## 依赖关系

- 此命令依赖 Phase 1 已完成的工具：
  - `agora_create_motion`
  - `agora_list_motions`
  - `agora_get_history`
  - `agora_get_result`
  - `agora_vote`（投票子命令）