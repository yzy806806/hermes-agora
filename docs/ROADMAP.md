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
- 10.5a: E2E 端到端接入测试 ✅ 测试完成 + 5 个 bug 已修复，待 review 确认

## 状态：Phase 10 全部完成，待发布 v0.10.0（2026-06-11）

- 864/864 测试通过
- 所有审查完成
- 发布任务已创建 (t_d0817d2d)
