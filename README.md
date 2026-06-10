# Agora 🏛️

> AI-Powered Multi-Agent Collaboration Platform

Agora 是一个独立的多代理协作平台，让多个 AI Agent 以结构化讨论、协商、投票的方式共同完成项目开发和维护。

它可以接收一个初步的项目设想，自动组织多代理讨论设计、分解任务、分配开发、审查代码、发布到目标仓库——全程自动化，像一个真正的小型软件公司那样工作。

## 核心定位

**Agora 不是一个 Hermes 插件，而是一个独立平台。**

- Agora = 调度层（讨论 + 任务分发 + 项目管理），不关心 agent 在什么平台上跑
- Agent 只要注册到 Agora，不管底层是 Hermes、Docker 容器、Codex 还是任何能接 HTTP/WS 的东西
- Hermes 可以作为 Agora 的 agent 之一接入，但 Agora 不依赖 Hermes 的任何内部机制

## 架构

```
                    ┌──────────────────────────┐
                    │     Agora Coordinator     │
                    │  (调度 + 存储 + 智能引导)   │
                    │   Web Dashboard :8080     │
                    └────────────┬─────────────┘
                                 │ WebSocket / REST
          ┌──────────────────────┼──────────────────────┐
          ↓                      ↓                      ↓
   ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
   │  Agent A    │       │  Agent B    │       │  Agent C    │
   │  (Hermes)   │       │  (Docker)   │       │  (Codex)    │
   │  planner    │       │  developer  │       │  reviewer   │
   └─────────────┘       └─────────────┘       └─────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 ↓
                    ┌──────────────────────────┐
                    │    Target Project        │
                    │  (GitHub / 本地目录 / 网站) │
                    └──────────────────────────┘
```

## 核心特性

### 🎯 全自动项目开发

扔一个初步设想进去，Agora 自动完成：

1. **讨论** — 多代理讨论架构设计、技术选型、开发路线
2. **分解** — coordinator 将讨论结果拆分为可执行任务图 (TaskGraph)
3. **分配** — 根据角色分工（capability）自动分配任务给 agent
4. **执行** — agent 并行开发、写代码、审查
5. **发布** — 代码审查通过后推送到目标仓库

### 🔌 Agent 无关

不绑定任何特定 AI 平台。任何能通过 API 通信的 agent 都可以注册：

- Hermes Agent（通过 AgoraClient 接入）
- Docker 容器中的独立 agent
- Codex / Claude Code 等 CLI agent
- 自定义 HTTP agent

**注册协议 (v0.9.3)**：
- Token 认证 — 注册获得 agent_token，WS 连接携带 token 验证
- 审批流程 — 支持 auto-approve（开发）/ require-approval（生产）
- 心跳保活 — 每 30s HEARTBEAT 更新负载 + 在线状态
- 能力声明 — 标准化的 capability taxonomy（code/test/review/deploy 等）

### 🧩 任务执行引擎

讨论关闭后自动生成任务图并分配给 agent：

- **TaskGraph** — DAG 结构，支持依赖管理
- **能力匹配** — 按 agent 声明的 capabilities 分配任务
- **状态机** — PENDING → ASSIGNED → RUNNING → DONE → ACCEPTED/REJECTED
- **WebSocket 驱动** — TASK_ASSIGNED / TASK_STATUS / TASK_COMPLETED 消息

### ⚡ 并行任务执行 (Phase 10)

多个独立任务同时执行，充分利用多代理架构：

- **DAG 感知调度** — 自动识别可并行任务，尊重依赖顺序
- **执行槽位** — 按 agent 的 max_concurrent_tasks 限制并发
- **资源冲突检测** — 文件级读写锁，避免并行任务冲突
- **失败隔离** — 单任务失败不影响独立任务，可配置重试策略

### 🔐 RBAC 权限控制 (Phase 10)

替代单一 admin token，实现细粒度角色权限：

- **五角色体系** — SUPERADMIN / ADMIN / AGENT / OBSERVER / PLUGIN
- **15 细粒度权限** — agent:register, discussion:create, task:execute 等
- **JWT Token** — 创建、轮换、撤销，支持作用域限定（租户/IP/过期/次数）
- **审计日志** — 所有安全事件可追溯

### 🔌 插件生态 (Phase 10)

无需修改核心代码即可扩展 Agora：

- **Hook 系统** — 20+ 生命周期事件（discussion/task/agent/system）
- **入口点发现** — `pip install agora-plugin-xxx` 自动发现加载
- **扩展点** — 自定义投票方法、任务验证器、API 端点、讨论策略
- **沙箱隔离** — 导入限制 + 超时执行

### 📊 每个代理独立的 API 限速

为每个接入的代理设定模型 API 调用速度限制（TPM），避免某个 agent 消耗过多资源：

- Token Bucket 算法 — 支持 burst（默认 1.5x）
- 双重保障 — Coordinator 端 tracking + Client 端本地预检
- WS 通知 — 80% 警告 / 100% 限流 / 恢复通知

### 🌐 Web Dashboard

可视化观测平台状态：

- 代理讨论记录（实时 / 历史）
- 项目开发进度（任务看板）
- 各代理状态和资源消耗
- Prometheus 指标图表（Chart.js）
- SSE 实时事件流
- 设置页面（角色配置、项目目标、限速策略等）

### 🔭 可观测性

全面了解 Coordinator 内部状态：

- **Metrics** — 20+ Prometheus 指标（讨论数、Agent 连接、投票统计等）
- **Events** — 17 种结构化事件类型，JSON Lines 输出 + SSE 实时推送
- **Traces** — 每个请求自动注入 X-Trace-Id，贯穿 REST + WebSocket 链路

### 🏢 多租户

一个 Coordinator 实例管理多个隔离的讨论空间：

- 每个租户独立的 SQLite 数据库（天然隔离）
- 租户级资源限制（Agent 数、并发讨论数）
- 向后兼容：不带 tenant_id 的请求默认使用 "default" 租户

### 📁 项目目标灵活

Agora 管理的"项目"不限于 GitHub 仓库：

- **GitHub 仓库** — 自动 PR、review、release
- **本地目录** — 直接操作文件系统
- **本地网站** — 静态站生成 + 部署
- **任意文件集合** — 文档库、配置集等

## 讨论流程

```
1. 用户 → 提交项目设想（"开发一个文档知识库 DocMind"）
2. Coordinator 分析设想 → 发起讨论议题
3. 各 Agent 独立思考并发言（架构、技术选型、开发路线）
4. Coordinator 智能引导讨论（分歧点聚焦 / 共识推进）
5. 讨论收敛 → 投票决策
6. Coordinator 自动生成任务图 → 分配给各 Agent
7. Agent 并行执行 → 产出代码 / 文档 / 配置
8. Review Agent 审查 → 通过后发布到目标项目
9. 持续巡检 → 自动维护和迭代
```

## 智能讨论

- **实时讨论评估** — 共识度、分歧点检测
- **共识提前判断** — 跳过剩余轮次直接投票
- **魔鬼代言人** — 自动生成反对观点
- **分歧点聚焦** — 引导讨论关键分歧
- **动态轮次调整** — 根据讨论质量增减轮次
- **9 种投票方式** — 简单多数、排序选择、批准、评分等

## 自我进化闭环

```
讨论 → 结论沉淀 → 策略优化 → 下次讨论更聪明
```

**Coordinator 进化**：
- 学会什么时候该推进投票
- 学会识别跑偏讨论
- 记住哪些 Agent 擅长什么领域

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

## 部署

### Docker 部署（推荐）

```bash
docker compose up -d
```

### 本地运行

```bash
# 安装
pip install agora

# 启动 coordinator
agora serve --port 8080

# Agent 接入
agora agent --coordinator http://localhost:8080 --name developer
```

## 配置

```yaml
# config.yaml
coordinator:
  host: 0.0.0.0
  port: 8080
  db_path: data/agora.db
  require_approval: false      # Phase 9.3: true 则新 agent 需审批

agents:
  - name: planner
    type: hermes                # Phase 9.3: hermes|docker|cli|custom
    model: deepseekv4pro
    tpm_limit: 10               # Phase 9.4: 每分钟最多 token 数
    tpm_burst_factor: 1.5       # Phase 9.4: 突发倍数
  
  - name: developer
    type: docker
    image: agora-agent:latest
    tpm_limit: 20
    tpm_burst_factor: 2.0
  
  - name: reviewer
    type: codex
    tpm_limit: 15

project:
  type: github                  # github / local / website
  repo: yzy806806/docmind
  branch: main

discussion:
  default_rounds: 3
  default_voting: simple_majority
  smart_discussion: true
  devils_advocate: true

rbac:                           # Phase 10.2: RBAC 配置
  enforce: false                # true 启用严格权限检查，false 仅记录
  default_role: agent           # 无 RBAC 配置时的默认角色
  admin_token_role: superadmin  # AGORA_ADMIN_TOKEN 映射的角色

plugins:                        # Phase 10.3: 插件配置
  enabled: true                 # 是否启用插件系统
  disabled: []                  # 禁用的插件名称列表
  sandbox:
    max_memory_mb: 100          # 插件内存限制
    max_cpu_seconds: 30         # 插件 CPU 时间限制
```

## 项目状态

📦 v0.10.0 — 并行任务执行 + RBAC 权限控制 + 插件生态

🚧 下一阶段：集成测试 + 性能优化 (Phase 11)

## 插件开发

详见 [docs/DESIGN-phase10.md](docs/DESIGN-phase10.md) Part C。

创建插件只需：

1. 继承 `AgoraPlugin`，实现 `on_load` / `on_unload`
2. 声明 `PluginManifest`（name, version, capabilities）
3. 在 `pyproject.toml` 注册 `agora.plugins` 入口点
4. `pip install` 后 Agora 自动发现并加载

## License

MIT
