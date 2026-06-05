# Phase 1: Agent 注册/注销机制设计

## 概述

设计 Agent 注册/注销机制：Agent 如何加入/退出讨论、身份认证、状态管理。

## 1. Agent 身份模型

### 1.1 核心属性

```python
class AgentInfo(BaseModel):
    agent_id: str           # 唯一标识 (Hermes profile name)
    name: str               # 显示名称
    hermes_endpoint: str    # Hermes Gateway 地址
    model: str              # 当前使用模型
    capabilities: list[str] # 能力列表 (web, code, etc.)
    role: AgentRole         # 角色
    registered_at: datetime # 注册时间
    last_seen: datetime     # 最后活跃时间
    is_online: bool         # 在线状态
    api_key: str            # 认证密钥 (仅存储哈希)
```

### 1.2 Agent 角色

```python
class AgentRole(str, Enum):
    COORDINATOR = "coordinator"   # 调度者（主持讨论）
    PARTICIPANT = "participant"   # 普通参与者
    EXPERT = "expert"             # 专家（特定领域）
    DEVIL_ADVOCATE = "devil_advocate"  # 魔鬼代言人
    OBSERVER = "observer"         # 观察者（仅观看）
```

## 2. 认证机制

### 2.1 API Key 认证

```python
class AuthConfig(BaseSettings):
    # Coordinator 服务端配置
    require_api_key: bool = True
    api_key_header: str = "X-Agora-Key"
    
    # Agent 客户端配置
    coordinator_url: str = "ws://localhost:8970"
    agent_api_key: str = ""  # 从配置读取
    
class AgentAuth:
    """Agent 认证工具类"""
    
    @staticmethod
    def generate_api_key() -> str:
        """生成新的 API Key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """哈希存储"""
        return hashlib.sha256(api_key.encode()).hexdigest()
```

### 2.2 认证流程

```
HTTP 注册流程:
1. Agent POST /agents/register
   - Header: X-Agora-Key: <api_key>
   - Body: { agent_id, name, hermes_endpoint, model, capabilities }

2. Coordinator 验证 API Key
   - 匹配成功: 注册 Agent，返回 AgentInfo
   - 匹配失败: 401 Unauthorized

WebSocket 握手:
1. Agent 连接 ws://host:port/ws/{agent_id}?token=<api_key>
2. Coordinator 验证 token
3. 验证通过: 接受连接，设置 is_online=true
4. 验证失败: 关闭连接
```

## 3. 注册流程

### 3.1 HTTP 注册

```python
@router.post("/agents/register", response_model=AgentRegisterResponse)
async def register_agent(
    request: AgentRegisterRequest,
    x_api_key: str = Header(None, alias="X-Agora-Key")
):
    """Agent 注册接口"""
    
    # 1. 验证 API Key
    if not await auth_service.validate_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # 2. 检查是否已注册
    existing = await storage.get_agent(request.agent_id)
    if existing:
        # 更新现有 Agent 信息
        await storage.update_agent(request)
        return AgentRegisterResponse(
            status="updated",
            agent=existing,
            message="Agent info updated"
        )
    
    # 3. 创建新 Agent
    agent = AgentInfo(
        agent_id=request.agent_id,
        name=request.name,
        hermes_endpoint=request.hermes_endpoint,
        model=request.model,
        capabilities=request.capabilities,
        role=AgentRole(request.role) if request.role else AgentRole.PARTICIPANT,
        registered_at=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        is_online=False,
        api_key=auth_service.hash_api_key(x_api_key)
    )
    
    await storage.register_agent(agent)
    
    # 4. 返回 WebSocket 连接信息
    return AgentRegisterResponse(
        status="registered",
        agent=agent,
        ws_endpoint=f"ws://{host}/ws/{agent.agent_id}",
        message="Registration successful"
    )
```

### 3.2 WebSocket 注册握手

```python
class WSMessageType(str, Enum):
    REGISTER = "REGISTER"
    AUTH_HANDSHAKE = "AUTH_HANDSHAKE"
    # ...

async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """WebSocket 端点 - 包含认证握手"""
    
    # 1. 从 query 参数获取 token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    # 2. 验证 token
    agent = await auth_service.validate_ws_token(agent_id, token)
    if not agent:
        await websocket.close(code=4002, reason="Invalid token")
        return
    
    # 3. 接受连接并注册
    await websocket.accept()
    await connection_manager.connect(agent_id, websocket)
    
    # 4. 更新在线状态
    await storage.set_agent_online(agent_id, True)
    
    # 5. 发送欢迎消息
    await connection_manager.send(agent_id, {
        "type": "WELCOME",
        "payload": {
            "agent_id": agent_id,
            "server_time": datetime.utcnow().isoformat(),
            "active_motions": await storage.list_motions(status=MotionStatus.DISCUSSING)
        }
    })
    
    # 6. 开始心跳监控
    asyncio.create_task(heartbeat_monitor(agent_id, websocket))
```

## 4. 注销流程

### 4.1 主动注销

```python
# WebSocket 消息
class DeregisterMessage(BaseModel):
    type: Literal["DEREGISTER"]
    reason: Optional[str] = "user_request"  # user_request, finished, error

async def handle_deregister(agent_id: str, message: DeregisterMessage):
    """处理 Agent 主动注销"""
    
    # 1. 标记为离线
    await storage.set_agent_online(agent_id, False)
    
    # 2. 关闭 WebSocket 连接
    connection_manager.disconnect(agent_id)
    
    # 3. 广播离线通知
    await connection_manager.broadcast({
        "type": "AGENT_OFFLINE",
        "payload": {"agent_id": agent_id, "reason": message.reason}
    })
    
    # 4. 可选: 保留注册信息但标记为离线
    # 或完全删除: await storage.deregister_agent(agent_id)
```

### 4.2 被动注销 (断开连接)

```python
async def on_agent_disconnect(agent_id: str, reason: str = "connection_lost"):
    """Agent 断开连接处理"""
    
    # 1. 标记为离线
    await storage.set_agent_online(agent_id, False)
    await storage.update_last_seen(agent_id)
    
    # 2. 从活跃连接中移除
    connection_manager.disconnect(agent_id)
    
    # 3. 检查是否在讨论中
    active_motions = await storage.get_agent_active_motions(agent_id)
    if active_motions:
        # 广播该 Agent 暂时离线
        await connection_manager.broadcast({
            "type": "AGENT_TEMPORARILY_OFFLINE",
            "payload": {
                "agent_id": agent_id,
                "active_motions": [m.id for m in active_motions]
            }
        })
```

## 5. 状态管理

### 5.1 Agent 在线状态

```python
class AgentState(str, Enum):
    REGISTERED = "registered"    # 已注册，离线
    ONLINE = "online"            # 在线，已连接
    AWAY = "away"                # 暂时离开（如超时前）
    DISCONNECTED = "disconnected"  # 已断开

# 数据库字段
# agents.is_online: bool
# agents.last_seen: datetime
# agents.state: AgentState
```

### 5.2 心跳机制

```python
# WebSocket 心跳消息
PING = {"type": "PING", "timestamp": "..."}
PONG = {"type": "PONG", "timestamp": "..."}

HEARTBEAT_INTERVAL = 30  # 秒
HEARTBEAT_TIMEOUT = 90  # 秒 (3次心跳间隔)

async def heartbeat_monitor(agent_id: str, websocket: WebSocket):
    """心跳监控协程"""
    
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            
            # 发送 PING
            await websocket.send_json({"type": "PING", "timestamp": time.time()})
            
            # 等待 PONG (使用 wait_for 超时)
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
                if msg.get("type") == "PONG":
                    await storage.update_last_seen(agent_id)
            except asyncio.TimeoutError:
                # 超时，标记为 AWAY
                logger.warning(f"Heartbeat timeout for {agent_id}")
                await storage.set_agent_state(agent_id, AgentState.AWAY)
                
    except asyncio.CancelledError:
        pass  # 连接正常关闭
```

### 5.3 状态查询 API

```python
@router.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """获取 Agent 状态"""
    agent = await storage.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "agent_id": agent_id,
        "state": agent.state,
        "is_online": agent.is_online,
        "last_seen": agent.last_seen,
        "registered_at": agent.registered_at
    }

@router.get("/agents/online")
async def list_online_agents():
    """获取所有在线 Agent"""
    return await storage.list_agents(only_online=True)
```

## 6. 存储层设计

### 6.1 SQLite 表结构扩展

```python
async def init_db(db):
    """初始化数据库"""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hermes_endpoint TEXT,
            model TEXT,
            capabilities TEXT,  -- JSON array
            role TEXT DEFAULT 'participant',
            api_key_hash TEXT,
            
            -- 状态管理
            is_online INTEGER DEFAULT 0,
            state TEXT DEFAULT 'registered',
            registered_at TEXT,
            last_seen TEXT,
            
            UNIQUE(agent_id)
        );
        
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE,
            created_at TEXT,
            expires_at TEXT,
            is_active INTEGER DEFAULT 1
        );
        
        CREATE INDEX IF NOT EXISTS idx_agents_state ON agents(state);
        CREATE INDEX IF NOT EXISTS idx_agents_online ON agents(is_online);
    """)
```

### 6.2 核心方法

```python
class Storage:
    # Agent 管理
    async def register_agent(self, agent: AgentInfo) -> None
    async def update_agent(self, agent: AgentInfo) -> None
    async def deregister_agent(self, agent_id: str) -> None
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]
    async def list_agents(self, only_online: bool = False) -> list[AgentInfo]
    
    # 状态管理
    async def set_agent_online(self, agent_id: str, online: bool) -> None
    async def set_agent_state(self, agent_id: str, state: AgentState) -> None
    async def update_last_seen(self, agent_id: str) -> None
    
    # API Key 管理
    async def create_api_key(self) -> str  # 返回原始 key
    async def validate_api_key(self, key: str) -> bool
    async def revoke_api_key(self, key_hash: str) -> None
```

## 7. Hermes 插件集成

### 7.1 Hook 实现

```python
async def on_session_start(ctx) -> None:
    """Agent 上线时向 Coordinator 注册"""
    
    # 1. 获取 Agent 配置
    agent_id = ctx.profile_name
    config = ctx.config.get("agora", {})
    
    # 2. 获取 Coordinator URL
    coordinator_url = config.get("coordinator_url", DEFAULT_COORDINATOR_URL)
    api_key = config.get("api_key")
    
    if not api_key:
        logger.warning("No API key configured for Agora")
        return
    
    # 3. 发送 HTTP 注册请求
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"{coordinator_url.replace('ws://', 'http://')}/agents/register",
            json={
                "agent_id": agent_id,
                "name": config.get("name", agent_id),
                "hermes_endpoint": config.get("hermes_endpoint", "http://localhost:8080"),
                "model": config.get("model", "default"),
                "capabilities": config.get("capabilities", [])
            },
            headers={"X-Agora-Key": api_key}
        )
    
    # 4. 建立 WebSocket 连接
    # (后续 Phase 2 实现)
    logger.info(f"Agora: Agent {agent_id} registered with coordinator")


async def on_session_end(ctx) -> None:
    """Agent 下线时注销"""
    
    agent_id = ctx.profile_name
    config = ctx.config.get("agora", {})
    coordinator_url = config.get("coordinator_url", DEFAULT_COORDINATOR_URL)
    
    # 发送注销消息
    async with aiohttp.ClientSession() as session:
        await session.delete(
            f"{coordinator_url.replace('ws://', 'http://')}/agents/{agent_id}"
        )
    
    logger.info(f"Agora: Agent {agent_id} deregistered from coordinator")
```

## 8. 错误处理

### 8.1 错误码定义

```python
class AgoraErrorCode(str, Enum):
    # 认证错误 (4xxx)
    INVALID_API_KEY = "INVALID_API_KEY"
    MISSING_API_KEY = "MISSING_API_KEY"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    # Agent 错误 (5xxx)
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_ALREADY_REGISTERED = "AGENT_ALREADY_REGISTERED"
    AGENT_OFFLINE = "AGENT_OFFLINE"
    
    # 连接错误 (6xxx)
    WS_CONNECTION_FAILED = "WS_CONNECTION_FAILED"
    HEARTBEAT_TIMEOUT = "HEARTBEAT_TIMEOUT"
```

### 8.2 错误响应格式

```python
class ErrorResponse(BaseModel):
    type: Literal["ERROR"]
    code: AgoraErrorCode
    message: str
    details: Optional[dict] = None

# WebSocket 错误示例
{
    "type": "ERROR",
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid",
    "details": {"agent_id": "agent-1"}
}
```

## 9. API 汇总

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /agents/register | 注册 Agent |
| DELETE | /agents/{agent_id} | 注销 Agent |
| GET | /agents | Agent 列表 |
| GET | /agents/{agent_id} | Agent 详情 |
| GET | /agents/{agent_id}/status | Agent 状态 |
| GET | /agents/online | 在线 Agent |
| POST | /keys/generate | 生成 API Key |
| DELETE | /keys/{key_hash} | 撤销 API Key |
| WebSocket | /ws/{agent_id}?token=xxx | 实时通信 |

## 10. 下一步 (Phase 2)

1. 实现 Coordinator WebSocket 服务器
2. 实现 Agent Client 客户端库
3. 实现完整的心跳机制
4. 实现多 Agent 讨论管理
5. 集成 Hermes 插件 hooks