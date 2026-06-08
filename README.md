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
2. **分解** — coordinator 将讨论结果拆分为可执行任务
3. **分配** — 根据角色分工自动分配任务给 agent
4. **执行** — agent 并行开发、写代码、审查
5. **发布** — 代码审查通过后推送到目标仓库

### 🔌 Agent 无关

不绑定任何特定 AI 平台。任何能通过 API 通信的 agent 都可以注册：

- Hermes Agent（通过插件接入）
- Docker 容器中的独立 agent
- Codex / Claude Code 等 CLI agent
- 自定义 HTTP agent

### 📊 每个代理独立的 API 限速

为每个接入的代理设定模型 API 调用速度限制（TPM），避免某个 agent 消耗过多资源。

### 🌐 Web Dashboard

可视化观测平台状态：

- 代理讨论记录（实时 / 历史）
- 项目开发进度（任务看板）
- 各代理状态和资源消耗
- 设置页面（角色配置、项目目标、限速策略等）

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
agora-server --port 8080

# Agent 接入
agora-agent --coordinator http://localhost:8080 --name developer
```

## 配置

```yaml
# config.yaml
coordinator:
  host: 0.0.0.0
  port: 8080
  db_path: data/agora.db

agents:
  - name: planner
    type: hermes
    model: deepseekv4pro
    tpm_limit: 10         # 每分钟最多 10 次 LLM 调用
  
  - name: developer
    type: docker
    image: agora-agent:latest
    tpm_limit: 20
  
  - name: reviewer
    type: codex
    tpm_limit: 15

project:
  type: github            # github / local / website
  repo: yzy806806/docmind
  branch: main

discussion:
  default_rounds: 3
  default_voting: simple_majority
  smart_discussion: true
  devils_advocate: true
```

## 项目状态

📦 v0.7.0 — 讨论引擎 + 投票 + Docker 部署（作为 Hermes 插件）

🚧 下一阶段：独立化改造 + 任务执行引擎 + Web Dashboard

## License

MIT
