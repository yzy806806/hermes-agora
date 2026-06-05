# Phase 1: Coordinator FastAPI 服务设计

## 概述

设计 Coordinator 服务的 FastAPI 架构：HTTP REST API + WebSocket 实时通信。

## 1. 项目结构

```
coordinator/
├── __init__.py           # 包初始化
├── main.py               # FastAPI 入口
├── config.py             # 配置管理
├── models.py             # Pydantic 数据模型
├── router.py             # HTTP REST 路由
├── ws.py                 # WebSocket 处理
├── state.py              # 讨论状态机
└── storage.py            # SQLite 存储层
```

## 2. 配置 (config.py)

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = False
    
    # 数据库
    db_path: str = "data/agora.db"
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    # 讨论配置
    default_rounds: int = 3
    default_voting_method: str = "simple_majority"
    speak_timeout_seconds: int = 120
    vote_timeout_seconds: int = 60
    
    class Config:
        env_prefix = "AGORA_"

settings = Settings()
```

## 3. 数据模型 (models.py)

### 3.1 通用消息格式

```python
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    REGISTER = "REGISTER"
    DEREGISTER = "DEREGISTER"
    NEW_MOTION = "NEW_MOTION"
    SPEAK = "SPEAK"
    BROADCAST = "BROADCAST"
    REQUEST_VOTE = "REQUEST_VOTE"
    VOTE = "VOTE"
    RESULT = "RESULT"
    ERROR = "ERROR"
    PING = "PING"
    PONG = "PONG"

class WSMessage(BaseModel):
    type: MessageType
    motion_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
```

### 3.2 Agent 模型

```python
class AgentInfo(BaseModel):
    agent_id: str
    name: str
    hermes_endpoint: str
    model: str
    capabilities: list[str] = []
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    is_online: bool = False

class AgentRegisterRequest(BaseModel):
    agent_id: str
    name: str
    hermes_endpoint: str = "http://localhost:8080"
    model: str
    capabilities: list[str] = []
```

### 3.3 Motion 模型

```python
from enum import Enum

class MotionStatus(str, Enum):
    DRAFT = "draft"
    DISCUSSING = "discussing"
    VOTING = "voting"
    CLOSED = "closed"

class VotingMethod(str, Enum):
    SIMPLE_MAJORITY = "simple_majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"

class Stance(str, Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    NEUTRAL = "neutral"

class VoteChoice(str, Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"

class MotionCreateRequest(BaseModel):
    title: str
    description: str
    context: Optional[str] = None
    rounds: int = 3
    voting_method: VotingMethod = VotingMethod.SIMPLE_MAJORITY

class Motion(BaseModel):
    id: str
    title: str
    description: str
    context: Optional[str]
    rounds: int
    voting_method: VotingMethod
    status: MotionStatus = MotionStatus.DRAFT
    current_round: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3.4 发言与投票

```python
class SpeakRequest(BaseModel):
    motion_id: str
    round: int
    stance: Stance
    content: str
    evidence: list[dict[str, Any]] = []

class VoteRequest(BaseModel):
    motion_id: str
    vote: VoteChoice
    confidence: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = None
```

## 4. 存储层 (storage.py)

### 4.1 SQLite 表结构

```python
import aiosqlite
from datetime import datetime

class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    hermes_endpoint TEXT,
                    model TEXT,
                    capabilities TEXT,  -- JSON array
                    registered_at TEXT,
                    is_online INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS motions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    context TEXT,
                    rounds INTEGER,
                    voting_method TEXT,
                    status TEXT DEFAULT 'draft',
                    current_round INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    motion_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    round INTEGER,
                    stance TEXT,
                    content TEXT,
                    evidence TEXT,  -- JSON array
                    timestamp TEXT,
                    FOREIGN KEY (motion_id) REFERENCES motions(id),
                    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
                );
                
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    motion_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    vote TEXT,
                    confidence REAL,
                    reason TEXT,
                    timestamp TEXT,
                    UNIQUE(motion_id, agent_id),
                    FOREIGN KEY (motion_id) REFERENCES motions(id),
                    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_messages_motion ON messages(motion_id);
                CREATE INDEX IF NOT EXISTS idx_votes_motion ON votes(motion_id);
            """)
```

### 4.2 核心 CRUD 方法

```python
    # Agent 操作
    async def register_agent(self, agent: AgentInfo) -> None:
    async def deregister_agent(self, agent_id: str) -> None:
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
    async def list_agents(self) -> list[AgentInfo]:
    async def set_agent_online(self, agent_id: str, online: bool) -> None:
    
    # Motion 操作
    async def create_motion(self, motion: Motion) -> Motion:
    async def get_motion(self, motion_id: str) -> Optional[Motion]:
    async def list_motions(self, status: Optional[MotionStatus] = None) -> list[Motion]:
    async def update_motion_status(self, motion_id: str, status: MotionStatus) -> None:
    async def increment_round(self, motion_id: str) -> int:
    
    # Message 操作
    async def add_message(self, motion_id: str, agent_id: str, round: int, 
                          stance: str, content: str, evidence: list) -> None:
    async def get_messages(self, motion_id: str) -> list[dict]:
    
    # Vote 操作
    async def add_vote(self, motion_id: str, agent_id: str, vote: str, 
                       confidence: float, reason: Optional[str]) -> None:
    async def get_votes(self, motion_id: str) -> list[dict]:
    async def has_voted(self, motion_id: str, agent_id: str) -> bool:
```

## 5. 状态机 (state.py)

```python
from enum import Enum
from typing import Optional
from .models import MotionStatus, Motion, VoteChoice
from .storage import Storage

class StateMachine:
    def __init__(self, storage: Storage):
        self.storage = storage
    
    async def transition(self, motion_id: str, event: str) -> MotionStatus:
        """状态转换"""
        motion = await self.storage.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        
        old_status = motion.status
        
        if old_status == MotionStatus.DRAFT and event == "start":
            new_status = MotionStatus.DISCUSSING
        elif old_status == MotionStatus.DISCUSSING and event == "round_complete":
            if motion.current_round >= motion.rounds:
                new_status = MotionStatus.VOTING
            else:
                new_status = MotionStatus.DISCUSSING
        elif old_status == MotionStatus.VOTING and event == "all_voted":
            new_status = MotionStatus.CLOSED
        else:
            raise ValueError(f"Invalid transition: {old_status} + {event}")
        
        await self.storage.update_motion_status(motion_id, new_status)
        return new_status
    
    async def can_speak(self, motion_id: str, agent_id: str) -> bool:
        """检查 Agent 是否可以发言"""
        motion = await self.storage.get_motion(motion_id)
        if not motion or motion.status != MotionStatus.DISCUSSING:
            return False
        # TODO: 检查该轮次是否已发言
        return True
    
    async def can_vote(self, motion_id: str, agent_id: str) -> bool:
        """检查 Agent 是否可以投票"""
        motion = await self.storage.get_motion(motion_id)
        if not motion or motion.status != MotionStatus.VOTING:
            return False
        if await self.storage.has_voted(motion_id, agent_id):
            return False
        return True
```

## 6. WebSocket 处理 (ws.py)

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, agent_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[agent_id] = websocket
    
    def disconnect(self, agent_id: str):
        self.active_connections.pop(agent_id, None)
    
    async def send(self, agent_id: str, message: dict):
        if agent_id in self.active_connections:
            await self.active_connections[agent_id].send_json(message)
    
    async def broadcast(self, message: dict, exclude: list[str] = None):
        exclude = exclude or []
        for agent_id, ws in self.active_connections.items():
            if agent_id not in exclude:
                await ws.send_json(message)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """WebSocket 端点"""
    await manager.connect(agent_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(agent_id, message)
    except WebSocketDisconnect:
        manager.disconnect(agent_id)
        await on_agent_disconnect(agent_id)

async def handle_message(agent_id: str, message: dict):
    """处理 WebSocket 消息"""
    msg_type = message.get("type")
    
    if msg_type == "PING":
        await manager.send(agent_id, {"type": "PONG"})
    elif msg_type == "SPEAK":
        await handle_speak(agent_id, message)
    elif msg_type == "VOTE":
        await handle_vote(agent_id, message)
    # ... 其他消息类型
```

## 7. HTTP 路由 (router.py)

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from .models import (
    AgentRegisterRequest, AgentInfo, 
    MotionCreateRequest, Motion, MotionStatus,
    SpeakRequest, VoteRequest
)
from .storage import Storage
from .ws import manager
from .state import StateMachine

router = APIRouter()
storage = Storage("data/agora.db")
state_machine = StateMachine(storage)

# --- Agent API ---

@router.post("/agents/register", response_model=AgentInfo)
async def register_agent(request: AgentRegisterRequest):
    """Agent 注册"""
    agent = AgentInfo(
        agent_id=request.agent_id,
        name=request.name,
        hermes_endpoint=request.hermes_endpoint,
        model=request.model,
        capabilities=request.capabilities
    )
    await storage.register_agent(agent)
    return agent

@router.delete("/agents/{agent_id}")
async def deregister_agent(agent_id: str):
    """Agent 注销"""
    await storage.deregister_agent(agent_id)
    return {"status": "ok"}

@router.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """已注册 Agent 列表"""
    return await storage.list_agents()

# --- Motion API ---

@router.post("/motions", response_model=Motion)
async def create_motion(request: MotionCreateRequest):
    """创建议题"""
    import uuid
    motion = Motion(
        id=str(uuid.uuid4()),
        title=request.title,
        description=request.description,
        context=request.context,
        rounds=request.rounds,
        voting_method=request.voting_method,
        status=MotionStatus.DRAFT
    )
    await storage.create_motion(motion)
    return motion

@router.get("/motions", response_model=List[Motion])
async def list_motions(status: MotionStatus = None):
    """议题列表"""
    return await storage.list_motions(status)

@router.get("/motions/{motion_id}", response_model=Motion)
async def get_motion(motion_id: str):
    """议题详情"""
    motion = await storage.get_motion(motion_id)
    if not motion:
        raise HTTPException(status_code=404, detail="Motion not found")
    return motion

@router.post("/motions/{motion_id}/start")
async def start_motion(motion_id: str):
    """开始讨论"""
    await state_machine.transition(motion_id, "start")
    # 广播 NEW_MOTION 给所有在线 Agent
    motion = await storage.get_motion(motion_id)
    await manager.broadcast({
        "type": "NEW_MOTION",
        "motion_id": motion_id,
        "payload": motion.model_dump()
    })
    return {"status": "started"}

@router.get("/motions/{motion_id}/history")
async def get_history(motion_id: str):
    """讨论历史"""
    messages = await storage.get_messages(motion_id)
    votes = await storage.get_votes(motion_id)
    return {"messages": messages, "votes": votes}

@router.get("/motions/{motion_id}/result")
async def get_result(motion_id: str):
    """讨论结果"""
    motion = await storage.get_motion(motion_id)
    if motion.status != MotionStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Motion not closed yet")
    votes = await storage.get_votes(motion_id)
    # 计算结果...
    return {"decision": "...", "votes": votes}
```

## 8. FastAPI 入口 (main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .config import settings
from .storage import Storage
from .router import router
from .ws import websocket_endpoint, manager

storage = Storage(settings.db_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    await storage.init_db()
    yield
    # 关闭时
    pass

app = FastAPI(
    title="Hermes Agora Coordinator",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api/v1")
app.add_api_websocket_route("/ws/{agent_id}", websocket_endpoint)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def main():
    import uvicorn
    uvicorn.run(
        "coordinator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

if __name__ == "__main__":
    main()
```

## 9. 启动方式

```bash
# 直接运行
python -m coordinator.main

# 或使用入口点
agora-coordinator

# 通过环境变量配置
export AGORA_HOST=0.0.0.0
export AGORA_PORT=8765
export AGORA_DB_PATH=data/agora.db
```

## 10. 边界情况处理

| 场景 | 处理 |
|------|------|
| Agent 在讨论中掉线 | WebSocket 断开后标记 `is_online=false`，跳过其发言轮次 |
| 议题创建后无人响应 | 超时后自动关闭，返回 `no_consensus` |
| 投票时 Agent 离线 | 记录已投票 Agent，未全部投票则等待超时 |
| 并发发言冲突 | 队列机制，按 Agent ID 排序决定发言顺序 |
| 数据库锁定 | 使用 aiosqlite 异步操作，避免阻塞 |

## 11. 依赖关系

```
main.py
  ├── config.py (Settings)
  ├── router.py
  │     ├── storage.py (Storage)
  │     ├── state.py (StateMachine)
  │     └── ws.py (ConnectionManager)
  └── ws.py
        └── storage.py
```