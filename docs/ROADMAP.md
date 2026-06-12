# Agora Development Roadmap — Owner's Vision

> 这是项目所有者的开发构思，供 planner 和团队参考规划下一阶段。

## 核心方向转变

Agora 是纯平台，**自身不包含任何 agent**。所有角色（包括 coordinator）都是外部接入的 agent。

Agora 只提供：
- 通信基础设施（消息路由、讨论状态机、存储）
- 认证与权限管理
- 项目管理（目标设定、进度追踪）

Coordinator 也是外部 agent，只是承担"主持人"角色，可以被替换为不同实现。

### 1. 平台化

Agora 是一个独立平台，可以用 Docker 部署也可以本地跑。可以接入各种 agent，Hermes 是其中之一但不是唯一。

- Agent 注册机制：任何能通过 HTTP/WebSocket 通信的 agent 都能接入
- 不依赖 Hermes 的 kanban、memory、skills 等内部机制
- Coordinator 自身负责调度、存储、讨论管理

### 2. 全自动项目开发

Agora 可以设定终极目标：全自动维护开发某个项目。为此，在讨论的基础上，需要能够调度多代理并行干活。

完整流程：
```
用户扔设想 → 讨论设计 → 任务分解 → 并行开发 → 代码审查 → 发布
```

- Coordinator 从讨论结果自动生成任务图
- 多个 agent 可以并行执行不同任务
- 类似当前的小团队（planner/dev-merger/reviewer/releaser），但完全自动化

### 3. 代理 API 限速

每个接入的代理可以设定模型 API 调用速度限制（TPM），避免资源浪费和费用失控。

### 4. Web Dashboard

需要一个 Web 界面，用于：
- 观测项目进展
- 查看代理们的讨论记录（实时 + 历史）
- 项目开发进度（任务看板）
- 各种设置页面（角色配置、项目目标、限速策略等）

### 5. 项目目标灵活

Agora 管理的"项目"不限于 GitHub 仓库：
- GitHub 仓库（自动 PR、review、release）
- 本地目录（直接操作文件系统）
- 本地网站（静态站生成 + 部署）
- 任意文件集合

## 下一阶段优先级建议

1. **独立化改造** — 从 Hermes 插件解耦，变成独立服务 ✅ Phase 9.1 已完成
2. **任务执行引擎** — 讨论结果 → 任务图 → 自动分配 → 执行 → 验收（Phase 9.2 设计完成，待开发）
3. **Agent 注册协议** — 定义 agent 注册、心跳、能力声明（Phase 9.3 待开发）
4. **API 速率限制** — TPM 限速（Phase 9.4 待开发）
5. **Web Dashboard** — 讨论记录、项目进度、设置界面（Phase 11+）

## Agent 自我进化策略（2026-06-10 决策 + 调研结论）

**Agora 必须让接入的 agent 保留自我进化能力（memory + skill），这是 Agora 区别于"无状态 LLM 调度器"的核心价值。**

### 调研结论：Hermes Kanban 的 memory/skill 可用性

- **Kanban worker（子代理）**：通过 `hermes -p <profile> chat -q` 启动，不走 cron scheduler，**不会传 `skip_memory=True`**。`memory`、`skills_list`、`skill_view`、`skill_manage` 工具全部正常可用。✅
- **Cron 任务（maintainer）**：走 cron scheduler，传了 `skip_memory=True`，**memory 工具被跳过初始化**。maintainer 无法写 memory，但 skill 工具正常。❌ memory / ✅ skill
- **结论**：只需给 profile 配置 `toolsets` 包含 `memory` + `skills`，子代理就能自我进化。maintainer 的 memory 问题可以通过直接读写 `~/.hermes/profiles/maintainer/memory.md` 文件绕过。

### Agora 的设计方向

Agora coordinator 不替代 agent 的 skill/memory 机制——那是 agent 自己的事。Agora 只需要：

1. **Session 持久化** — 每个 agent 的每次"任务执行"是一个 session，coordinator 存储完整的 session 数据（输入、输出、工具调用、错误）。agent 可以在下次任务时检索历史 session，实现"经验积累"。
2. **Agent 状态协议** — 注册时声明 capabilities（包括是否支持 skill/memory），coordinator 分配任务时考虑 agent 的经验积累。
3. **不重新发明轮子** — 用 Hermes 的 agent 自带 skill/memory，用 OpenClaw 的 agent 自带它的持久化机制。Agora 只提供 session 记录和检索 API。

### 实操：当前团队

已完成的配置：
- 五个 profile 的 `toolsets` 全部设为 `['hermes-cli', 'memory', 'skills']`
- 五个 SOUL 全部加入自我进化规则（写 memory + 生成 skill + 提 SOUL 建议）
- maintainer SOUL 加入 ROADMAP 同步 + skill 检查

预期效果：团队越跑越聪明——token 截断经验、代码审查清单、发布流程 check 都会沉淀为 skill 和 memory，不再每次从零开始。

**不自己开发 Agent Runtime。** Agora 只做 Coordinator（讨论 + 调度），agent 全部用现成的。

原因：
- Hermes、OpenClaw 等各有专门团队维护，我们维护不了另一个 agent 框架
- Agora 的核心价值是"多 agent 协作调度"，不是"又一个 agent 框架"
- 通过标准协议接入，任何实现了协议的 agent 都能加入讨论和执行任务

Agora 定义标准通信协议（WebSocket + JSON），agent 侧只需实现一个薄适配层。

候选接入的 agent 平台（由 planner 调研确定优先级和可行性）：
- **Hermes** — 有 TUI + CLI，skill/memory/tool 机制成熟，当前团队已在使用
- **OpenClaw** — CLI 驱动，需调研接入方式
- **PicoClaw** — 待调研
- 其他热门 agent CLI 工具

当前团队迁移路径：
- 5 个 Hermes profile（maintainer/planner/dev-merger/reviewer/releaser）保留
- 触发方式从 kanban dispatcher 换成 Agora coordinator WebSocket 消息
- skill/memory/tool 全部保留，agent 还是 Hermes
- coordinator 角色（讨论主持 + 任务分发）由 Agora 内置实现，或由 Hermes profile 担任

## 参考：当前团队结构

目前的子代理团队可以作为 Agora 的第一个真实测试案例：

| 角色 | 当前实现 | 目标 |
|------|---------|------|
| maintainer | Hermes profile + cron | Agora 注册 agent |
| planner | Hermes profile + cron | Agora 注册 agent |
| dev-merger | Hermes profile + cron | Docker 容器 agent |
| reviewer | Hermes profile + cron | Docker 容器 agent |
| releaser | Hermes profile + cron | Docker 容器 agent |

## Phase 9: 平台独立 + 任务执行引擎 + Agent 注册协议 (2026-06)

> 详细设计见 docs/DESIGN-phase9.md

### 目标

1. **平台独立化** — 从 Hermes 插件解耦为独立 pip 包 `agora`，支持 Docker 部署
2. **任务执行引擎** — 讨论结果自动生成任务图 → 分配 → 执行 → 验收
3. **Agent 注册协议** — 标准化注册、心跳、能力声明、Token 认证
4. **API 速率限制** — 每 Agent TPM 限制，客户端本地执行

### 不做什么

- 不做并行任务执行（Phase 10）
- 不做完整 RBAC（Phase 10+）
- 不做插件生态（Phase 10+）
- 不做 Web 管理界面（Phase 11+）

### 子任务拆分

- 9.1a-c: 平台独立（包重命名、Docker、配置） ✅ 已完成 (v0.9.0)
- 9.2a: 任务模型 + 存储 ✅ 已完成
- 9.2b: 任务生成器（LLM + 启发式回退）✅ 代码完成 + 审查通过
- 9.2c: 任务分配器 ✅ 已完成 (代码 + 审查通过)
- 9.2d-e: 任务执行、验证 ✅ 已完成 (代码 + 审查通过 + bugfix)
- 9.3a-c: Agent 注册协议（模型更新、注册认证、心跳能力）✅ 已完成 (v0.9.3)
- 9.4a-b: API 速率限制（令牌桶、客户端集成）✅ 已完成 (v0.9.3)
- 9.5a: 集成 + 文档更新 ✅ 已完成 (v0.9.4)

## 参考：未来用例

**DocMind** — 一个文档知识库项目，只有初步设想，等 Agora 成熟后扔给 Agora 全自动开发。

这就是 Agora 的价值：用户只需要一个想法，Agora 组织团队把想法变成现实。

## Phase 10: 并行任务执行 + RBAC + 插件生态 (2026-06)

> 详细设计见 docs/DESIGN-phase10.md

### 目标

1. **并行任务执行** — 基于 Phase 9.2 的任务 DAG，支持多个 agent 同时执行独立任务
2. **RBAC 权限控制** — 替换单一 admin token 为角色/权限矩阵
3. **插件生态系统** — 钩子系统 + 生命周期管理 + 扩展点注册

### 子任务拆分

- 10.1a-f: 并行执行引擎（模型更新、并行调度器、资源冲突检测、WS 消息）✅ 代码完成 + 审查通过 + 测试修复完成
- 10.2a-e: RBAC（中间件、令牌管理、审计日志、权限装饰器）✅ 代码完成 + 审查通过 + 测试修复完成
- 10.3a-e: 插件系统（ABC 基类、钩子系统、发现机制、沙箱、扩展注册）✅ 代码完成 + 审查通过 + 测试修复完成
- 10.4a-b: 集成 + 文档 ✅ 代码完成 + 审查通过 + 测试修复完成
- 10.5a: E2E 端到端接入测试 ✅ 全部完成（866/866 单元+集成测试通过，3 个 E2E WebSocket 测试需运行中的服务器）

## 状态：Phase 10 ✅ 已完成，v0.10.0 已发布（2026-06-11）

- v0.10.0 已发布至 GitHub: https://github.com/yzy806806/agora/releases/tag/v0.10.0
- 81 files committed, +6888/-63 lines
- 866/866 单元+集成测试通过
- 所有审查完成

## Phase 11: Web Dashboard（已规划）

> ROADMAP 优先级第 4 项：Web Dashboard | 详细设计见 docs/DESIGN-phase11.md

### 目标

1. **观测项目进展** — 实时查看 agent 们的讨论记录
2. **项目开发进度** — 任务看板视图
3. **设置页面** — 角色配置、项目目标、限速策略等
4. **Dashboard 登录** — JWT 认证，分角色 UI
5. **Agent 管理** — 审批/配置/TPM/并发
6. **插件管理** — 启用/禁用/健康检查
7. **审计日志** — 可过滤查询

### 子任务拆分

- 11.1a: Task query endpoints ✅ 代码完成 + Batch 1 审查通过
- 11.1b: Agent config endpoints ✅ 代码完成 + 审查通过（923/926 tests, 7/7 new tests pass）
- 11.1c: Plugin management endpoints ✅ 代码完成 + Batch 1 审查通过
- 11.1d: Audit query endpoint ✅ 代码完成 + Batch 1 审查通过
- 11.2a: Dashboard login endpoint ✅ 代码完成（由 11.5a integration 覆盖实现 auth_router.py）
- 11.2b: Dashboard WebSocket auth ✅ 代码完成 + Batch 1 审查通过
- 11.3a: Dashboard HTML shell + CSS ✅ 代码完成 + Batch 2 审查通过（修复后）
- 11.3b: JS core modules ✅ 代码完成 + Batch 2 审查通过（CRITICAL: auth.js login overlay class 已修复）
- 11.3c: Overview + Discussions pages ✅ 代码完成 + Batch 2 审查通过
- 11.4a: Task kanban page + kanban component ✅ 代码完成 + Batch 2 审查通过
- 11.4b: Agent management page ✅ 代码完成 + Batch 2 审查通过
- 11.4c: Plugin + Audit pages ✅ 代码完成 + Batch 2 审查通过（修复后）
- 11.5a: Integration wiring + backward compat ✅ 代码完成 + Batch 1 审查通过

## 状态：Phase 11 ✅ 已完成，v0.11.0 已发布（2026-06-11）

- v0.11.0 已发布至 GitHub: https://github.com/yzy806806/agora/releases/tag/v0.11.0
- 57 files, +3911/-68 lines
- 923/926 测试通过（3 个 E2E WebSocket 测试需运行中的服务器，已知问题）
- 18 AsyncMock 垃圾文件已清理
- 所有审查完成

## Phase 12: Multi-platform Agent Integration ✅

> ROADMAP 优先级第 1 项：Multi-platform Agent Integration | 详细设计见 docs/DESIGN-phase12.md

### 目标

1. **Agora Agent SDK（Python）** — 独立 pip 包 `agora-agent-sdk`，供任何 agent runtime 导入连接 Agora
2. **Hermes Bridge** — Hermes 配置文件的桥接守护进程，自动注册并映射 kanban↔Agora WS 消息
3. **Generic CLI Bridge** — 通用 CLI agent 桥接（Codex、Claude Code、OpenClaw 等），PTY 子进程 + ToolAdapter
4. **Node.js SDK** — npm 包 `@agora/agent-sdk`，解锁 JS/TS 生态
5. **Agent 自我进化** — Session 持久化 API + Project 制品存储，agent 可检索历史积累经验
6. **Production Hardening** — 修复 E2E WebSocket 测试、版本断言

### 子任务拆分

- 12.1a-f: Agent SDK（Python）✅ 已完成
- 12.2a-c: Hermes Bridge ✅ 已完成
- 12.3a-e: CLI Bridge ✅ 已完成
- 12.4a-c: Node.js SDK ✅ 已完成
- 12.5a-d: Agent 自我进化 ✅ 已完成
- 12.6a-b: Production Hardening ✅ 已完成
- 12.7a-d: 集成 + 文档 ✅ 已完成

### Design Decisions

1. **独立 SDK 包** — 与 coordinator 包解耦，agent 无需安装完整 Agora
2. **Hermes Bridge 作为守护进程** — Hermes 本身不修改，桥接层翻译 kanban↔Agora WS
3. **CLI Bridge 使用 PTY 子进程** — 不修改 CLI agent 本身，ToolAdapter 统一工具调用格式
4. **Session 持久化在 Agora** — agent 通过 API 查询自己的历史，不替代 agent 自身的 memory 机制
5. **制品存储为简单 KV** — 足够存 conventions/notes/findings，大型制品留在 git/project 中

## 状态：Phase 12 ✅ 全部审查通过，待发布 v0.12.0（2026-06-12）

- 所有 18 个 dev-merger 子任务代码已写完（因 protocol violation 未走完 kanban 流程，已手动归档）
- Review 任务(t_aeb7482c)已完成 — 审查发现 3 个问题：
  - 🔴 CRITICAL: cli-bridge 测试与实现 API 不匹配（PtyManager vs PTYManager）→ ✅ 已修复
  - 🟡 MEDIUM: hermes-bridge 测试字段名错误（sample_task.id → task_id）+ mock 路径错误 → ✅ 已修复
  - 🟢 MINOR: Node.js SDK 未使用的 undici 依赖 → ✅ 已修复
- Fix 任务(t_1a659920)已完成 — 3 个审查问题全部修复
- Fix review 任务(t_56847ff7)已完成 — 审查通过
- Review 任务(t_f21169bf)已完成 — 审查通过（PtyManager rewrite + test mock fixes）
- 935/935 测试通过（全量回归通过）
- 发布任务(t_493d9a70)已创建给 releaser — 发布 v0.12.0

## Phase 13: Full-auto Dev Loop + Dashboard Enhancement（已规划）

> 详细设计见 docs/DESIGN-phase13.md

### 目标

1. **全自动化开发闭环 E2E** — 连接所有 Phase 12 组件，实现从用户设想到代码发布的端到端自动化
2. **Dashboard 增强** — 实时 WS 推送、图表、通知系统
3. **Go/Rust SDK** — 扩展语言生态
4. **多租户生产部署** — Docker Compose 多租户支持

### 子任务拆分

- 13.1a-h: Pipeline Orchestrator（PipelineRun 模型、状态机、代码审查集成、发布集成、REST API、WS 消息、存储、测试）
- 13.2a-d: Dashboard 实时 WebSocket 推送（事件广播、替换 SSE、重连逻辑）
- 13.3a-d: Dashboard 图表（Metrics 历史 API、Chart.js 集成、实时更新）
- 13.4a-e: Dashboard 通知系统（模型+存储、NotificationManager、REST API、UI、测试）
- 13.5a-e: Go SDK（包结构、Client 实现、协议模型、示例、测试）
- 13.6a-e: Rust SDK（Cargo 包结构、Client 实现、EventHandler trait、示例、测试）
- 13.7a-d: 多租户生产部署（docker-compose.prod.yaml、健康检查、DEPLOYMENT.md、冒烟测试）
- 13.8a-d: 集成 + 文档（ARCHITECTURE.md、API.md、ROADMAP.md、CHANGELOG.md）

## 状态：已纳入开发计划（由 planner 于 2026-06-12 确认）
