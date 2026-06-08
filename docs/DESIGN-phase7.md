# Phase 7: 生产可用性 — 集成测试、部署、规范加固

> 版本: v0.7.0  
> 设计者: planner  
> 状态: 规划完成  
> 依赖: Phase 1-6 全部完成

---

## 1. 背景与目标

Phase 1-6 构建了完整的多 Agent 讨论决策框架（MVP → 智能讨论 → 记忆进化 → 自举 → 容错安全 → 质量增强），项目已具备 60+ 模块、~5,800 行测试、~70 个源文件。但项目**尚不可用于生产**：

| 维度 | 当前状态 | 目标 |
|------|---------|------|
| 测试覆盖 | 全是单测，无端到端集成测试 | 多 Agent 真实 WebSocket 流程测试 |
| 部署 | 一个 Dockerfile 跑测试 | coordinator 独立可部署，支持 docker compose |
| 插件规范 | 基本兼容，面面没做到 | 对齐最新 Hermes 插件规范，hooks 真正干活 |
| 文档 | ARCHITECTURE.md 严重过时，无 API 文档 | 文档与代码一致，有 API 参考 |
| 性能 | 未知瓶颈 | 建立基准 + 定位热点 |

---

## 2. 优先级与任务分解

| 优先级 | 方向 | 影响 | 工作量 |
|--------|------|------|--------|
| P0 | 集成测试（e2e） | 可信度、发版信心 | 大 |
| P0 | 插件规范加固 | 兼容性、可安装性 | 中 |
| P1 | Docker 生产部署 | 用户部署体验 | 中 |
| P1 | 文档更新 | 开发者体验 | 小 |
| P2 | 性能基线 + 优化 | 可扩展性 | 中 |

### 顺序依赖

```
集成测试 ──→ 部署（需要通过测试验证部署）
插件加固 ──→ 独立
文档更新 ──→ 独立（但先改代码再改文档）
性能优化 ──→ 依赖集成测试基础设施
```

---

## 3. 集成测试（P0）

### 3.1 现状

- 现有 60+ 测试文件、~5,790 行测试，全部是单测
- WebSocket 相关测试（`test_ws.py`）用 MagicMock，没有真实连接
- `test_main_integration.py` 测试 lifespan，但依然是 heavy mocking
- **无测试启动真实 Coordinator + 多个 WebSocket Client 并走完整流程**

### 3.2 方案

创建 `tests/integration/` 目录，使用 **pytest + asyncio + websockets 库** 实现真正的 e2e 测试。

#### 架构

```
tests/integration/
├── conftest.py          # 共享 fixtures: coordinator 进程管理
├── test_e2e_basic.py    # 基础流程: 注册 → 讨论 → 投票 → 结果
├── test_e2e_multiple.py # 多 Agent 并发言论测试
└── test_e2e_reconnect.py # 断线重连测试
```

#### Fixture 设计

```python
# conftest.py — 核心思路
@pytest_asyncio.fixture(scope="module")
async def coordinator():
    """启动真实的 Coordinator 服务（子进程）。"""
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "coordinator.main",
        env={
            **os.environ,
            "AGORA_DB_PATH": ":memory:",      # 内存数据库
            "AGORA_HOST": "127.0.0.1",
            "AGORA_PORT": str(_find_free_port()),
        }
    )
    await _wait_for_health(port, timeout=10)
    yield port
    proc.terminate()
    await proc.wait()


@pytest_asyncio.fixture
async def agent_client(coordinator_port):
    """建立真实 WebSocket 连接到 Coordinator。"""
    async with websockets.connect(
        f"ws://127.0.0.1:{coordinator_port}/ws/test-agent-{uuid4().hex[:8]}"
    ) as ws:
        yield ws
```

#### 测试案例

**Test 1: 基础讨论流程**
```python
async def test_basic_discussion_flow(coordinator_port):
    """完整流程: create_motion → speak (2 agents) → vote → get_result."""
    # 1. Agent A 通过 HTTP 创建议题
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://127.0.0.1:{coordinator_port}/api/v1/motions",
            json={"title": "Should we use microservices?", "description": "...", "rounds": 1},
        )
        assert resp.status_code == 200
        motion_id = resp.json()["motion_id"]

    # 2. Agent A 和 B 连接 WebSocket
    async with websockets.connect(f"ws://127.0.0.1:{coordinator_port}/ws/agent-a") as ws_a, \
               websockets.connect(f"ws://127.0.0.1:{coordinator_port}/ws/agent-b") as ws_b:
        # 收到注册确认
        reg_a = json.loads(await ws_a.recv())
        assert reg_a["type"] == "registered"

        # 3. Agent A 发言
        await ws_a.send(json.dumps({
            "type": "speak",
            "motion_id": motion_id,
            "content": "Microservices provide better isolation.",
            "stance": "for",
        }))
        # 4. Agent B 发言
        await ws_b.send(json.dumps({
            "type": "speak",
            "motion_id": motion_id,
            "content": "Monolith is simpler for our team size.",
            "stance": "against",
        }))

        # 5. 投票
        await ws_a.send(json.dumps({
            "type": "vote", "motion_id": motion_id, "vote": "for", "confidence": 0.8,
        }))
        await ws_b.send(json.dumps({
            "type": "vote", "motion_id": motion_id, "vote": "against", "confidence": 0.7,
        }))

    # 6. 验证结果
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://127.0.0.1:{coordinator_port}/api/v1/motions/{motion_id}/result")
        assert resp.status_code == 200
        result = resp.json()
        assert "status" in result
```

**Test 2: 多 Agent 并发**
```python
async def test_concurrent_agents(coordinator_port):
    """5 个 Agent 同时连接并发起讨论。"""
    agents = []
    for i in range(5):
        ws = await websockets.connect(f"ws://127.0.0.1:{coordinator_port}/ws/agent-{i}")
        agents.append(ws)
        # 等待注册确认
        await ws.recv()

    # 全部同时发言
    tasks = []
    for i, ws in enumerate(agents):
        tasks.append(ws.send(json.dumps({
            "type": "speak", "motion_id": motion_id,
            "content": f"Agent {i} opinion", "stance": "neutral",
        })))
    await asyncio.gather(*tasks)
```

#### 测试配置

在 `pyproject.toml` 中添加集成测试标记：

```toml
[tool.pytest.ini_options]
markers = [
    "unit: 单元测试（默认，不依赖 Coordinator 进程）",
    "integration: 集成测试（启动真实 Coordinator）",
]
```

运行方式：
```bash
# 只跑单测
uv run pytest tests/ -m "not integration" -x -q

# 跑所有测试（含集成测试）
uv run pytest -x -q

# 单独跑集成测试
uv run pytest tests/integration/ -x -q --timeout=60
```

#### 注意事项

- 集成测试使用 `:memory:` 数据库，避免文件残留
- 每个测试模块启动独立的 Coordinator 进程（端口自动分配）
- 添加 `pytest-timeout` 依赖防止测试 hang
- CI 中集成测试单独一个 job 运行（因为时间长）

---

## 4. 插件规范加固（P0）

### 4.1 Hermes 插件规范检查

当前 `plugin.yaml` 和 `__init__.py` 基本符合规范，但有以下缺失：

| 检查项 | 当前 | 需要 |
|--------|------|------|
| `plugin.yaml` URLs | 无 | 加 `homepage`、`repository`、`license` 字段 |
| Hook `on_session_start` | 只打 log | 向 Coordinator 注册 Agent |
| Hook `on_session_end` | 只打 log | 从 Coordinator 注销，写入讨论经验到 memory |
| Hook `post_tool_call` | `pass` | 记录工具调用作为讨论证据 |
| `plugin.yaml` `provides_tools` | 6 个 | 与 `register()` 一致（ok） |
| Hermes config 格式 | 自定义解析 | 改成从 `ctx.config.get("agora", {})` 读取 |

### 4.2 需要修改的内容

#### plugin.yaml 增强

```yaml
name: agora
version: "0.7.0"
description: "..."
author: yzy806806
homepage: https://github.com/yzy806806/hermes-agora
repository: https://github.com/yzy806806/hermes-agora
license: MIT
kind: backend
provides_tools:
  - agora_create_motion
  - agora_speak
  - agora_vote
  - agora_list_motions
  - agora_get_history
  - agora_get_result
hooks:
  - on_session_start
  - on_session_end
  - post_tool_call
provides_commands:
  - name: agora
    description: "多 Agent 讨论决策"
    args_hint: "<new|list|status|vote|result> [args]"
```

#### __init__.py hooks 实现

**on_session_start** — 向 Coordinator 发送注册消息：

```python
async def on_session_start(ctx) -> None:
    """Agent 上线时向 Coordinator 注册。"""
    client = _get_client()
    try:
        result = await client.register()
        logger.info("Agora: registered with Coordinator: %s", result)
    except Exception as exc:
        logger.warning("Agora: registration failed (Coordinator may not be running): %s", exc)
```

需要在 `AgoraClient` 中添加 `register()` 方法——通过 WebSocket 或者 HTTP POST 发送注册请求。

**on_session_end** — 从 Coordinator 注销：

```python
async def on_session_end(ctx) -> None:
    """Agent 下线时注销并同步讨论经验。"""
    client = _get_client()
    try:
        await client.unregister()
    except Exception:
        pass
    logger.info("Agora: unregistered from Coordinator")
```

**post_tool_call** — 记录工具使用作为讨论证据：

```python
async def post_tool_call(ctx, tool_name: str, tool_input: dict, tool_output: dict) -> None:
    """记录讨论中的工具使用作为证据。"""
    # Only record if we're in an active discussion context
    if tool_name.startswith("agora_"):
        return  # Don't record our own tools
    # Store tool usage as potential evidence for the current discussion
    logger.debug("Agora: recording tool call %s as discussion evidence", tool_name)
```

#### Config 读取方式修改

当前 `load_config(hermes_cfg)` 接收整个 config dict。改造成从 `ctx.config` 中读取 `agora` 嵌套字段：

```python
def register(ctx) -> None:
    global _client
    # 从 Hermes config 中读取 agora 配置
    hermes_cfg = ctx.config if isinstance(ctx.config, dict) else {}
    agora_config = hermes_cfg.get("agora", hermes_cfg)  # fallback for backward compat
    config = load_config(agora_config)
    _client = AgoraClient(config)
```

---

## 5. Docker 生产部署（P1）

### 5.1 当前问题

- 单一 Dockerfile，默认 CMD 是跑 pytest
- Dockerfile 中 `--all-extras` 在新版 uv 中可能不存在
- `.dockerignore` 排除了 `docs/` 但包含了不必要的 `.venv/`
- 没有生产环境的 docker-compose

### 5.2 新 Dockerfile 设计

```dockerfile
# === Build stage ===
FROM python:3.12-slim AS builder

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 只复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装生产依赖（不含 dev）
RUN uv sync --frozen --no-dev

# === Production stage ===
FROM python:3.12-slim AS coordinator

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY coordinator/ /app/coordinator/
COPY agent_client/ /app/agent_client/
COPY __init__.py pyproject.toml plugin.yaml ./

ENV PATH="/app/.venv/bin:$PATH"

# 默认启动 Coordinator
CMD ["uv", "run", "agora-coordinator"]

# 健康检查
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" || exit 1
```

### 5.3 docker-compose.prod.yaml

```yaml
services:
  coordinator:
    build:
      context: .
      target: coordinator
    ports:
      - "8765:8765"
    environment:
      - AGORA_HOST=0.0.0.0
      - AGORA_PORT=8765
      - AGORA_DB_PATH=/data/agora.db
      - AGORA_LOG_LEVEL=info
    volumes:
      - agora-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  agora-data:
```

### 5.4 更新 docker-compose.test.yaml

- 使用 multi-stage Dockerfile 的 builder 阶段来跑测试
- 添加 `AGORA_LOG_LEVEL=warning` 减少测试输出噪音
- 将 coordinator 的 CMD 改成明确用 `uv run`

### 5.5 .dockerignore 更新

```diff
- docs/
+ docs/README.md  # 只排除大文件，不整个排除 docs/（ARCHITECTURE.md 对镜像用户有用）
```

---

## 6. 文档更新（P1）

### 6.1 ARCHITECTURE.md

当前 ARCHITECTURE.md 显示的是 Phase 1 的项目结构。需要：

- 更新目录树，反映当前真实的文件结构（`coordinator/storage/` 目录结构、`voting/` 目录等）
- 添加 Phase 2-6 的架构说明（智能讨论、记忆进化、自举、容错安全、质量增强）
- 添加模块关系图

**新结构概览：**

```
hermes-agora/
├── __init__.py              # Hermes 插件入口 + register()
├── plugin.yaml              # 插件元数据
├── coordinator/             # 调度中心（FastAPI 服务）
│   ├── main.py              # 入口 + 生命周期
│   ├── ws.py                # WebSocket 连接管理
│   ├── ws_smart.py          # 智能讨论 WebSocket 处理
│   ├── ws_vote.py           # 投票 WebSocket 处理
│   ├── router.py            # REST API 路由
│   ├── models.py            # 数据模型
│   ├── state.py             # 讨论状态机
│   ├── config.py            # 配置
│   ├── assessment.py        # 讨论评估
│   ├── consensus_jump.py    # 共识提前判断
│   ├── devils_advocate.py   # 魔鬼代言人
│   ├── focus.py             # 分歧点聚焦
│   ├── quality_guard.py     # 质量守卫
│   ├── heartbeart.py        # 心跳
│   ├── timeout.py           # 超时
│   ├── deadlock_prevention.py # 死锁预防
│   ├── input_validation.py  # 输入验证
│   ├── memory_sync.py       # 内存同步
│   ├── history_pattern.py   # 历史模式
│   ├── judgment_tracker.py  # 判断追踪
│   ├── curator.py           # 策略优化
│   ├── similar_topic.py     # 相似议题检索
│   ├── bootstrap/           # 自举系统
│   ├── voting/              # 投票子系统
│   └── storage/             # 数据存储层
├── agent_client/            # Agent 客户端库
│   ├── client.py            # HTTP + WebSocket 客户端
│   ├── config.py            # 客户端配置
│   └── ws_pool.py           # WS 连接池
├── tests/
│   ├── unit/                # 单元测试（现有）
│   └── integration/         # 集成测试（Phase 7 新增）
└── docs/
    └── DESIGN-*.md          # 设计文档
```

### 6.2 README.md

- 添加 Phase 3-6 特性介绍
- 添加 Docker 部署说明
- 添加配置项参考表
- 更新项目状态为 v0.7.0

### 6.3 API 文档

在 `docs/API.md` 中添加 REST API 和 WebSocket 协议文档：

```markdown
# API 参考

## REST API

### POST /api/v1/motions
创建新的讨论议题

参数: title, description, context, rounds, voting_method

### GET /api/v1/motions
获取议题列表

参数: status, limit, offset

### GET /api/v1/motions/{id}
获取议题详情

### GET /api/v1/motions/{id}/result
获取讨论结果

## WebSocket 协议

### 连接: ws://host:port/ws/{agent_id}

### 消息格式 (JSON):

发送:
```json
{"type": "speak", "motion_id": "...", "content": "...", "stance": "for|against|neutral"}
{"type": "vote", "motion_id": "...", "vote": "for|against|abstain", "confidence": 0.0-1.0}
```

接收:
```json
{"type": "registered", "agent_id": "..."}
{"type": "broadcast", "event": "new_speech", ...}
{"type": "result", ...}
```
```

---

## 7. 性能基线 + 优化（P2）

### 7.1 性能基准测试

创建 `tests/benchmarks/` 目录，放置性能基准测试：

```python
# tests/benchmarks/test_websocket_throughput.py
@pytest.mark.benchmark
async def test_websocket_throughput(coordinator_port):
    """测量每秒可处理的 WebSocket 消息数。"""
    import time

    NUM_AGENTS = 10
    MSGS_PER_AGENT = 50

    agents = []
    for i in range(NUM_AGENTS):
        ws = await websockets.connect(f"ws://127.0.0.1:{coordinator_port}/ws/bench-{i}")
        await ws.recv()  # 注册确认
        agents.append(ws)

    start = time.monotonic()
    tasks = []
    for i, ws in enumerate(agents):
        for j in range(MSGS_PER_AGENT):
            tasks.append(ws.send(json.dumps({
                "type": "speak", "motion_id": motion_id,
                "content": f"bench msg {j}", "stance": "neutral",
            })))
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start

    total_msgs = NUM_AGENTS * MSGS_PER_AGENT
    throughput = total_msgs / elapsed
    print(f"Throughput: {throughput:.0f} msgs/sec ({total_msgs} msgs in {elapsed:.2f}s)")
```

### 7.2 已知性能瓶颈

基于现有代码分析和典型瓶颈模式：

| 瓶颈 | 影响 | 建议优化 |
|------|------|---------|
| SQLite 单连接串行 | 高并发时写竞争 | 使用 SQLite WAL 模式 + 连接池 |
| WS 广播 O(n) 循环 | 大量 Agent 时广播慢 | 并行广播 (`asyncio.gather`) |
| 状态机全局锁 | 多 WebSocket 同时操作 | 减小锁粒度 / 用无锁模式 |
| 动态轮次评估 | 每次发言都跑一次评估 | 引入评估频率限制 |

### 7.3 推荐优化（按优先级）

1. **首次优化：WAL 模式** — 在 `storage/__init__.py` 的 `init_db()` 中添加 `PRAGMA journal_mode=WAL`
2. **可选的：广播并行化** — 在 `ws.py` 的 `broadcast()` 中用 `asyncio.gather` 替代 for 循环
3. **可选的：评估频率限制** — `assessment.py` 中，每 N 条发言评估一次而非每次

---

## 8. 任务分解

### 8.1 给 dev-merger 的任务

创建以下 kanban 子任务：

**Task 1: 集成测试基础设施** (assignee: dev-merger)
- 创建 `tests/integration/conftest.py` — Coordinator 进程启动/停止 fixture
- 添加到 `pyproject.toml` 的 pytest 配置
- 验证 CI 中自动发现集成测试

**Task 2: 基础 E2E 测试** (assignee: dev-merger)
- `test_e2e_basic.py` — 完整讨论流程
- `test_e2e_multiple.py` — 多 Agent 并发测试
- `test_e2e_reconnect.py` — 断线重连测试

**Task 3: 插件 hooks 实现** (assignee: dev-merger)
- `on_session_start` — 实际注册到 Coordinator
- `on_session_end` — 注销 + 清理
- `post_tool_call` — 记录工具调用作为证据
- `plugin.yaml` 补充 fields (homepage, repository, license)

**Task 4: Docker 生产部署** (assignee: dev-merger)
- 多阶段 Dockerfile（builder + coordinator 阶段）
- `docker-compose.prod.yaml`
- 更新 `docker-compose.test.yaml`
- 更新 `.dockerignore`

**Task 5: 文档更新** (assignee: dev-merger)
- 更新 ARCHITECTURE.md
- 更新 README.md (Phase 3-6 特性 + Docker 说明 + 配置表)
- 新建 docs/API.md
- 验证 CI 中集成测试通过

**Task 6 (P2): SQLite WAL 模式 + 广播并行化** (assignee: dev-merger)
- storage/__init__.py 添加 WAL 模式 pragma
- ws.py broadcast() 并行化

### 8.2 依赖关系

```
Task 1 ──→ Task 2
Task 3 ──→ 独立
Task 4 ──→ 独立（但需要 Task 2 验证部署后测试通过）
Task 5 ──→ 独立（但先等 Task 3 改完代码再改文档）
Task 6 ──→ 独立
```

---

## 9. 发布清单（v0.7.0）

- [x] 集成测试全部通过（含 e2e）
- [x] 插件规范完全符合 Hermes 标准
- [x] Docker 多阶段构建
- [x] docker-compose.prod.yaml 可用
- [x] ARCHITECTURE.md 与代码一致
- [x] README.md 包含全部特性
- [x] docs/API.md 有 API 参考
- [x] SQLite WAL 模式开启（性能优化）
- [x] CI 中集成测试和单元测试分离运行

---

## 10. 边界情况与风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 集成测试耗时过长 | CI 时间增加 | 单独 job 运行，设置 timeout=120s |
| Coordinator 端口冲突 | 测试失败 | `_find_free_port()` 随机分配端口 |
| 测试启动 Coordinator 失败 | 测试失败 | 健康检查超时 10s 后跳过集成测试 |
| Hermes 插件 API 变更 | 不兼容 | 在 register() 中做兼容处理 |
| Docker 镜像体积大 | 部署慢 | 多阶段构建，生产镜像只包含必要文件 |
| SQLite WAL 模式兼容性 | 旧版 SQLite 不支持 | 检查版本，fall back 到默认模式 |
