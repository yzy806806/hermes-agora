# DESIGN-phase8.md — Phase 8: 可观测性与多租户

> 版本: v0.8.0-draft | 日期: 2026-06 | 作者: planner

## 背景

Phase 1-7 已完成 Agora 的核心讨论能力：投票决策、质量保证、容错安全、策略进化、自举系统。Agora 已经是一个"能讨论、会决策、有记忆、可进化"的多 Agent 讨论框架。

但两个关键缺口阻碍了 Agora 从内部工具走向可推广的平台：

1. **可观测性为零**：用户无法知道 Coordinator 内部发生了什么。讨论卡住了？Agent 掉线了？只能看日志猜。
2. **单实例限制**：一个 Coordinator 只能服务一个团队。无法同时跑"代码评审团队"和"文档翻译团队"。

这两个问题在竞品中普遍得到解决（AutoGen Studio、LangGraph Debugger、CrewAI Studio），是用户感知最强的短板。

## 方向评估

| 方向 | 重要性 | 紧迫性 | 可行性 | 推荐 |
|------|--------|--------|--------|------|
| 可观测性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Phase 8 核心 |
| 多租户 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Phase 8 核心 |
| 插件生态 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⏸ Phase 9 |
| 性能优化 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⏸ Phase 9/10 |
| 实际集成 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⏸ 贯穿各 Phase |

### 为什么先做可观测性+多租户

1. **可观测性是所有后续开发的前提** — 没有 visibility，debug 靠猜，优化靠蒙
2. **多租户解锁了"用 Agora 管理多个 AI 团队"** — 单实例只能玩一次
3. **插件生态需要稳定 API** — 在 Phase 8 稳定多租户 API 后，Phase 9 开放插件更合理
4. **性能优化没有观测数据就是玄学** — 先有 metrics 再优化

---

## Part A: 可观测性 (Observability)

### 设计目标

Agora 的可观测性覆盖三个层面：**指标(Metrics)**、**事件(Events)**、**追踪(Traces)**。

### A.1 Metrics（指标暴露）

采用 **Prometheus + OpenMetrics** 标准，通过 `/metrics` 端点暴露。

**核心 Metrics 列表**：

```
# 讨论指标
agora_discussions_total{status="discussing|voting|closed"}     # 讨论总数
agora_discussion_duration_seconds{method, outcome}               # 讨论耗时分布
agora_discussion_rounds_total{method}                           # 讨论轮次分布
agora_discussion_quality_score{motion_id}                       # 质量评分（gauge）

# Agent 指标
agora_agents_connected                                          # 当前连接数（gauge）
agora_agents_registered_total                                   # 累计注册数
agora_agent_disconnections_total{reason="timeout|error|clean"}  # 断连次数

# 投票指标
agora_votes_total{method, result="passed|rejected|tied"}        # 投票结果统计
agora_vote_participation_ratio                                  # 投票参与率（gauge）

# 工具调用指标
agora_tools_calls_total{tool, status}                           # 工具调用次数
agora_tools_call_duration_seconds{tool}                         # 工具调用耗时

# Coordinator 指标
agora_coordinator_uptime_seconds                                # 运行时间
agora_ws_messages_total{direction="in|out", type}               # WS 消息量
agora_db_size_bytes                                             # 数据库大小
agora_memory_sync_ops_total{status}                             # 记忆同步操作
```

### A.2 Events（结构化事件日志）

所有关键状态变更以结构化事件（JSON）输出。

```python
# 事件类型枚举
class EventType(Enum):
    # 讨论生命周期
    MOTION_CREATED = "motion.created"
    MOTION_STARTED = "motion.started" 
    MOTION_ASSESSING = "motion.assessing"
    MOTION_VOTING_STARTED = "motion.voting_started"
    MOTION_CLOSED = "motion.closed"
    
    # Agent 生命周期
    AGENT_REGISTERED = "agent.registered"
    AGENT_DISCONNECTED = "agent.disconnected"
    AGENT_TIMEOUT = "agent.timeout"
    
    # 讨论过程
    SPEAK = "speak"
    QUALITY_THRESHOLD_MET = "quality.threshold_met"
    QUALITY_INTERVENTION = "quality.intervention"
    CONSENSUS_JUMP = "consensus.jump"
    DEVILS_ADVOCATE_TRIGGERED = "devils_advocate.triggered"
    
    # 投票
    VOTE_CAST = "vote.cast"
    VOTE_RESULT = "vote.result"
    
    # 系统
    HEARTBEAT_LOST = "heartbeat.lost"
    DEADLOCK_DETECTED = "deadlock.detected"
    MEMORY_SYNC = "memory.sync"
```

**事件结构**：
```python
@dataclass
class Event:
    type: EventType
    motion_id: str
    timestamp: datetime
    agent_id: str | None
    data: dict                # 事件特有数据
    trace_id: str             # 关联追踪 ID
```

**事件输出**：
- 标准输出：JSON Lines（日志友好）
- WebSocket：通过 `discussions:{motion_id}:events` 频道实时推送
- 文件：可选持久化到 `events/YYYY-MM-DD.jsonl`

### A.3 Traces（请求追踪）

每次外部请求（REST API）和内部操作（讨论推进）携带 `trace_id`，贯穿整个流程。

```python
# 追踪上下文
@dataclass
class Trace:
    trace_id: str            # UUID
    motion_id: str | None    # 关联议题
    agent_id: str | None     # 发起方
    span_id: str             # 当前 span
    parent_span_id: str | None
    start_time: float
```

**Trace 在以下边界传播**：
- REST API 请求 → HTTP Header `X-Trace-Id`
- WebSocket 消息 → 消息体 `trace_id` 字段
- 记忆同步 → Hermes memory metadata
- 工具调用 → tool call arguments 的 `_trace_id`

### A.4 Dashboard（轻量 Web 面板）

基于现有 Coordinator 内嵌一个静态 HTML dashboard，在 `/dashboard` 路径提供。

**Dashboard 功能**：
1. **概览页**：当前讨论状态、Agent 连接数、最近事件流
2. **讨论详情页**：单讨论的时间线、发言历史、质量评分、投票结果
3. **Agent 列表页**：连接状态、历史参与、断连记录
4. **指标图表**：Prometheus metrics 的可视化（用 Chart.js）

**技术方案**：纯前端 HTML + JS，不引入新后端框架。通过 Coordinator 已有的 REST API 和 WebSocket 获取数据。用 Chart.js 渲染图表。

```python
# 新增 API 端点
GET  /api/v1/metrics          # Prometheus 格式 metrics
GET  /api/v1/events           # 最近的 events（支持 ?since=ISO&type=xxx 过滤）
GET  /api/v1/events/stream    # SSE 实时事件流
GET  /api/v1/discussions/{id}/timeline  # 讨论时间线
GET  /dashboard               # Dashboard HTML 页面
```

---

## Part B: 多租户 (Multi-Tenancy)

### 设计目标

一个 Coordinator 实例管理多个隔离的讨论空间（Tenant），每个 Tenant 有独立的 Agent 注册、议题列表、Storage 实例。

### B.1 租户模型

```python
@dataclass
class Tenant:
    tenant_id: str           # 唯一标识（slug, max 32 chars）
    name: str                # 显示名称
    created_at: datetime
    config: TenantConfig     # 租户级配置
    
@dataclass  
class TenantConfig:
    max_agents: int = 10         # 最大 Agent 数
    max_concurrent_discussions: int = 3  # 最大并发讨论
    default_voting_method: str = "simple_majority"
    allow_custom_voting_methods: bool = True
    quality_threshold: float = 0.6
    discussion_timeout_seconds: int = 3600
    auto_close_inactive_seconds: int = 86400  # 24h 自动关闭闲置讨论
```

### B.2 数据隔离方案

采用 **per-tenant SQLite** 方案（最简单的强隔离）：

```
data/
  global.db                    # 全局：租户列表、版本信息
  tenants/
    {tenant_id}/
      agora.db                 # 该租户的所有数据
      events/
        2026-06-09.jsonl
```

**优势**：
- 天然隔离，不存在数据泄漏风险
- 单租户可独立备份/迁移
- SQLite WAL 模式下多租户并发读写无冲突
- 简单——不改 Storage 架构，只改 `__init__`

**Storage 变更**：
```python
class StorageManager:
    """管理多租户 Storage 实例"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.global_db = GlobalStorage(data_dir / "global.db")
        self._tenants: dict[str, Storage] = {}
    
    async def get_tenant(self, tenant_id: str) -> Storage:
        """获取或懒创建租户的 Storage"""
        if tenant_id not in self._tenants:
            db_path = self.data_dir / "tenants" / tenant_id / "agora.db"
            self._tenants[tenant_id] = Storage(db_path)
        return self._tenants[tenant_id]
    
    async def create_tenant(self, tenant_id: str, name: str) -> Tenant:
        """创建新租户"""
        # 1. 写入 global.db
        # 2. 创建目录和空数据库
        # 3. 运行 schema migration
    
    async def list_tenants(self) -> list[Tenant]: ...
    async def delete_tenant(self, tenant_id: str): ...
```

### B.3 API 多租户路由

所有现有 API 端点加上 `/tenants/{tenant_id}` 前缀：

```
# 以前
POST /api/v1/motions
GET  /api/v1/motions/{motion_id}
WS   /ws?agent_id=xxx

# Phase 8
POST /api/v1/tenants/{tenant_id}/motions
GET  /api/v1/tenants/{tenant_id}/motions/{motion_id}
WS   /ws?agent_id=xxx&tenant_id=yyy

# 全局端点
GET  /api/v1/tenants            # 租户列表
POST /api/v1/tenants            # 创建租户
GET  /api/v1/metrics            # 全局或 ?tenant_id=xxx 过滤
```

**向后兼容**：保留不带 `tenant_id` 的端点（默认为 `"default"` 租户），Phase 8 零破坏性变更。

### B.4 WebSocket 租户隔离

```python
# ws_endpoint.py
async def websocket_endpoint(ws: WebSocket, agent_id: str, tenant_id: str = "default"):
    storage = await storage_manager.get_tenant(tenant_id)
    hub = get_tenant_hub(tenant_id)  # 每个租户独立的 ConnectionHub
    # ... 现有逻辑
```

**ConnectionHub 改为按租户隔离**：每个租户持有自己的 `{agent_id → WebSocket}` 映射，Agent 只能看到同租户的消息。

### B.5 多租户资源限制

```python
class TenantResourceGuard:
    """租户级资源限制"""
    
    async def check_agent_registration(self, tenant: Tenant) -> bool:
        """检查 Agent 数量是否超限"""
    
    async def check_discussion_start(self, tenant: Tenant) -> bool:
        """检查并发讨论是否超限"""
    
    def enforce(self, tenant: Tenant, resource: str) -> None:
        """强制执行限制，超限抛 429 Too Many Requests"""
```

---

## Part C: 集成方案

### C.1 两个 Part 的集成

多租户对可观测性的影响：
- Metrics 需要 `tenant_id` label 做维度切分
- Events 需要 `tenant_id` 字段用于过滤
- Dashboard 需要支持租户切换（`/dashboard?tenant_id=xxx`）

可观测性对多租户的依赖：
- 无——可观测性是全局能力，即使只有一个 `default` 租户也能提供价值

### C.2 API 变更汇总

```
# 新增
POST   /api/v1/tenants                                    # 创建租户
GET    /api/v1/tenants                                    # 租户列表
GET    /api/v1/tenants/{id}                               # 租户详情
DELETE /api/v1/tenants/{id}                               # 删除租户
GET    /api/v1/metrics                                    # Prometheus metrics
GET    /api/v1/events?since=&type=&tenant_id=             # 事件历史
GET    /api/v1/events/stream?tenant_id=                   # SSE 事件流
GET    /dashboard                                         # Dashboard HTML

# 修改（加 tenant 前缀，旧端点保留兼容）
POST   /api/v1/tenants/{tid}/motions                      # 创建议题
GET    /api/v1/tenants/{tid}/motions/{mid}                # 议题详情
GET    /api/v1/tenants/{tid}/motions/{mid}/timeline       # 讨论时间线
WS     /ws?agent_id=xxx&tenant_id=yyy                     # WebSocket

# 不变
/health                                                   # 健康检查
```

### C.3 Coordinator 主入口变更

```python
# main.py 新增
app.mount("/dashboard", StaticFiles(directory="coordinator/static"), name="dashboard")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")

# 初始化 StorageManager 替代单 Storage
storage_manager = StorageManager(data_dir=config.data_dir)
```

### C.4 新增文件

```
coordinator/
  storage/
    storage_manager.py       # 多租户 Storage 管理器
    global_store.py           # 全局数据（租户列表）
  observability/
    __init__.py
    metrics.py                # Prometheus metrics 注册 + 暴露
    events.py                 # 结构化事件定义 + 发布
    trace.py                  # Trace 上下文传播
  tenant/
    __init__.py
    manager.py                # 租户 CRUD + 生命周期
    guard.py                  # 资源限制守卫
    router.py                 # 租户 API 路由
  static/
    dashboard.html            # Dashboard 单页应用
    dashboard.js              # Dashboard 逻辑
```

---

## 子任务拆分

Phase 8 建议拆分为以下子任务（按依赖顺序）：

### 8.1 Metrics + Events + Traces 基础库 (dev-merger)
- `observability/metrics.py` — Prometheus 指标注册
- `observability/events.py` — 事件定义和发布
- `observability/trace.py` — Trace 上下文
- 集成到 router.py、ws_endpoint.py 的关键路径

### 8.2 多租户基础设施 (dev-merger)
- `storage/storage_manager.py` — 多租户 Storage
- `storage/global_store.py` — 全局数据库
- `tenant/manager.py` + `tenant/guard.py` + `tenant/router.py`
- WebSocket 租户隔离

### 8.3 Dashboard 前端 (dev-merger)
- `static/dashboard.html` + `dashboard.js`
- API: timeline、events/stream、metrics 端点
- 路由挂载和静态文件服务

### 8.4 集成 + 文档更新 (dev-merger)
- 所有模块集成到 main.py
- plugin.yaml 版本号 bump 到 0.8.0
- ARCHITECTURE.md、README.md 更新
- 测试更新

---

## 不做什么

- **不做复杂插件系统** — 留到 Phase 9
- **不做水平扩展** — 单实例多租户已经满足中期需求
- **不做 Web UI for 讨论** — Dashboard 是监控面板，不是讨论界面
- **不做用户认证** — 租户是逻辑隔离，不是安全隔离（Phase 10+ 的安全话题）
- **不做性能优化** — 等有 metrics 数据后再针对性优化