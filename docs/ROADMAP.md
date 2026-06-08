# Agora Development Roadmap — Owner's Vision

> 这是项目所有者的开发构思，供 planner 和团队参考规划下一阶段。

## 核心方向转变

Agora 不再是 Hermes 插件，而是一个**独立的多代理协作平台**。

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

1. **独立化改造** — 从 Hermes 插件解耦，变成独立服务
2. **任务执行引擎** — 讨论结果 → 任务图 → 自动分配 → 执行 → 验收
3. **Agent 注册协议** — 定义 agent 注册、心跳、能力声明
4. **Web Dashboard** — 讨论记录、项目进度、设置界面
5. **Docker 化 agent** — 容器化的 agent 模板，一键部署

## 参考：当前团队结构

目前的子代理团队可以作为 Agora 的第一个真实测试案例：

| 角色 | 当前实现 | 目标 |
|------|---------|------|
| maintainer | Hermes profile + cron | Agora 注册 agent |
| planner | Hermes profile + cron | Agora 注册 agent |
| dev-merger | Hermes profile + cron | Docker 容器 agent |
| reviewer | Hermes profile + cron | Docker 容器 agent |
| releaser | Hermes profile + cron | Docker 容器 agent |

## 参考：未来用例

**DocMind** — 一个文档知识库项目，只有初步设想，等 Agora 成熟后扔给 Agora 全自动开发。

这就是 Agora 的价值：用户只需要一个想法，Agora 组织团队把想法变成现实。
