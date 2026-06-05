# Phase 1: SQLite Storage Layer Design

## 概述

为 Hermes Agora 设计 SQLite 数据持久化层，支持多 Agent 讨论框架的存储需求。

## 1. 数据库架构

### 1.1 数据库文件

```
data/agora.db
```

配置文件路径: `coordinator/config.py` 中 `db_path: str = "data/agora.db"`

### 1.2 表结构总览

| 表名 | 说明 | 主键 |
|------|------|------|
| agents | Agent 注册信息 | agent_id |
| motions | 讨论议题 | id |
| messages | 发言记录 | id (自增) |
| votes | 投票记录 | id (自增) |

## 2. 表结构设计

### 2.1 agents 表

```sql
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hermes_endpoint TEXT,
    model TEXT,
    capabilities TEXT,        -- JSON 数组: ["web_search", "code_execution"]
    role TEXT DEFAULT 'expert',  -- moderator/expert/devil_advocate/neutral
    registered_at TEXT NOT NULL,
    is_online INTEGER DEFAULT 0,
    last_seen_at TEXT
);
```

**字段说明:**
- `agent_id`: 唯一标识，UUID 格式或自定义字符串
- `hermes_endpoint`: Agent 关联的 Hermes 网关地址
- `model`: 使用的模型名称
- `capabilities`: Agent 能力列表，JSON 格式存储
- `role`: 角色（moderator/expert/devil_advocate/neutral）
- `is_online`: 在线状态（0/1）
- `last_seen_at`: 最后活跃时间

### 2.2 motions 表

```sql
CREATE TABLE motions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    context TEXT,             -- 背景材料、约束条件
    rounds INTEGER NOT NULL DEFAULT 3,
    voting_method TEXT NOT NULL DEFAULT 'simple_majority',
    status TEXT NOT NULL DEFAULT 'draft',
    current_round INTEGER DEFAULT 0,
    decision TEXT,            -- adopted/rejected/no_consensus
    rationale TEXT,           -- 决策理由
    action_items TEXT,        -- JSON 数组: 行动项
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);
```

**字段说明:**
- `id`: UUID
- `rounds`: 讨论轮次
- `voting_method`: simple_majority/supermajority/unanimous/weighted
- `status`: draft → discussing → voting → closed
- `current_round`: 当前轮次（0 开始）
- `decision`: 最终决定
- `rationale`: 决策理由（closed 时填充）
- `action_items`: 行动项列表，JSON 格式

### 2.3 messages 表

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    round_num INTEGER NOT NULL,
    stance TEXT,              -- support/oppose/neutral
    content TEXT NOT NULL,
    evidence TEXT,            -- JSON 数组: [{"type": "web_search", "query": "..."}]
    timestamp TEXT NOT NULL,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_messages_motion ON messages(motion_id);
CREATE INDEX idx_messages_agent ON messages(agent_id);
CREATE INDEX idx_messages_round ON messages(motion_id, round_num);
```

**字段说明:**
- `round_num`: 发言所属轮次
- `stance`: 立场
- `content`: 发言内容
- `evidence`: 证据列表，JSON 格式

### 2.4 votes 表

```sql
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    vote TEXT NOT NULL,       -- yes/no/abstain
    confidence REAL,          -- 0.0-1.0
    reason TEXT,
    timestamp TEXT NOT NULL,
    UNIQUE(motion_id, agent_id),
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_votes_motion ON votes(motion_id);
```

**字段说明:**
- `confidence`: 投票信心度（0.0-1.0）
- `vote`: yes/no/abstain
- UNIQUE 约束确保每个 Agent 对每个 Motion 只能投一次

## 3. ORM/Query 接口

### 3.1 Storage 类设计

```python
import aiosqlite
import json
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

class Storage:
    """SQLite 存储层"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @asynccontextmanager
    async def _connection(self):
        """异步数据库连接上下文管理器"""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()
    
    async def init_db(self) -> None:
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(_SCHEMA_SQL)
            await db.commit()
```

### 3.2 Agent 操作

```python
    # --- Agent CRUD ---
    
    async def register_agent(
        self,
        agent_id: str,
        name: str,
        model: str,
        hermes_endpoint: str = "",
        capabilities: list[str] = None,
        role: str = "expert"
    ) -> dict:
        """注册新 Agent"""
        capabilities_json = json.dumps(capabilities or [])
        now = datetime.utcnow().isoformat()
        
        async with self._connection() as db:
            await db.execute("""
                INSERT INTO agents (agent_id, name, hermes_endpoint, model, 
                                    capabilities, role, registered_at, is_online)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, [agent_id, name, hermes_endpoint, model, 
                  capabilities_json, role, now])
            await db.commit()
        
        return {"agent_id": agent_id, "registered_at": now}
    
    async def get_agent(self, agent_id: str) -> Optional[dict]:
        """获取 Agent 信息"""
        async with self._connection() as db:
            async with db.execute(
                "SELECT * FROM agents WHERE agent_id = ?", [agent_id]
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def list_agents(self, online_only: bool = False) -> list[dict]:
        """列出 Agents"""
        query = "SELECT * FROM agents"
        if online_only:
            query += " WHERE is_online = 1"
        
        async with self._connection() as db:
            async with db.execute(query) as cursor:
                return [dict(row) async for row in cursor]
    
    async def set_agent_online(self, agent_id: str, online: bool) -> None:
        """设置 Agent 在线状态"""
        now = datetime.utcnow().isoformat()
        async with self._connection() as db:
            await db.execute("""
                UPDATE agents SET is_online = ?, last_seen_at = ? 
                WHERE agent_id = ?
            """, [1 if online else 0, now, agent_id])
            await db.commit()
    
    async def deregister_agent(self, agent_id: str) -> None:
        """注销 Agent"""
        async with self._connection() as db:
            await db.execute("DELETE FROM agents WHERE agent_id = ?", [agent_id])
            await db.commit()
```

### 3.3 Motion 操作

```python
    # --- Motion CRUD ---
    
    async def create_motion(
        self,
        title: str,
        description: str,
        rounds: int = 3,
        voting_method: str = "simple_majority",
        context: str = ""
    ) -> dict:
        """创建新议题"""
        import uuid
        motion_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        async with self._connection() as db:
            await db.execute("""
                INSERT INTO motions (id, title, description, context, 
                                    rounds, voting_method, status, 
                                    current_round, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'draft', 0, ?, ?)
            """, [motion_id, title, description, context, 
                  rounds, voting_method, now, now])
            await db.commit()
        
        return {"id": motion_id, "created_at": now}
    
    async def get_motion(self, motion_id: str) -> Optional[dict]:
        """获取议题详情"""
        async with self._connection() as db:
            async with db.execute(
                "SELECT * FROM motions WHERE id = ?", [motion_id]
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def list_motions(
        self, 
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """列出议题"""
        query = "SELECT * FROM motions"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with self._connection() as db:
            async with db.execute(query, params) as cursor:
                return [dict(row) async for row in cursor]
    
    async def update_motion_status(
        self, 
        motion_id: str, 
        status: str,
        decision: str = None,
        rationale: str = None,
        action_items: list[str] = None
    ) -> None:
        """更新议题状态"""
        now = datetime.utcnow().isoformat()
        
        # 构建动态 SQL
        updates = ["status = ?", "updated_at = ?"]
        params = [status, now]
        
        if decision is not None:
            updates.append("decision = ?")
            params.append(decision)
        if rationale is not None:
            updates.append("rationale = ?")
            params.append(rationale)
        if action_items is not None:
            updates.append("action_items = ?")
            params.append(json.dumps(action_items))
        if status == "closed":
            updates.append("closed_at = ?")
            params.append(now)
        
        params.append(motion_id)
        
        async with self._connection() as db:
            await db.execute(f"""
                UPDATE motions SET {', '.join(updates)} WHERE id = ?
            """, params)
            await db.commit()
    
    async def increment_round(self, motion_id: str) -> int:
        """增加轮次，返回新轮次号"""
        async with self._connection() as db:
            await db.execute("""
                UPDATE motions SET current_round = current_round + 1, 
                                   updated_at = ? WHERE id = ?
            """, [datetime.utcnow().isoformat(), motion_id])
            await db.commit()
            
            async with db.execute(
                "SELECT current_round FROM motions WHERE id = ?", [motion_id]
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
```

### 3.4 Message 操作

```python
    # --- Message CRUD ---
    
    async def add_message(
        self,
        motion_id: str,
        agent_id: str,
        round_num: int,
        stance: str,
        content: str,
        evidence: list[dict] = None
    ) -> int:
        """添加发言"""
        now = datetime.utcnow().isoformat()
        evidence_json = json.dumps(evidence or [])
        
        async with self._connection() as db:
            await db.execute("""
                INSERT INTO messages (motion_id, agent_id, round_num, 
                                     stance, content, evidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [motion_id, agent_id, round_num, stance, 
                  content, evidence_json, now])
            await db.commit()
            
            # 获取自增 ID
            async with db.execute("SELECT last_insert_rowid()") as cursor:
                row = await cursor.fetchone()
                return row[0]
    
    async def get_messages(
        self, 
        motion_id: str, 
        round_num: Optional[int] = None,
        agent_id: Optional[str] = None
    ) -> list[dict]:
        """获取发言列表"""
        query = "SELECT * FROM messages WHERE motion_id = ?"
        params = [motion_id]
        
        if round_num is not None:
            query += " AND round_num = ?"
            params.append(round_num)
        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        
        query += " ORDER BY timestamp ASC"
        
        async with self._connection() as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def count_messages_by_round(self, motion_id: str, round_num: int) -> int:
        """统计某轮发言数量"""
        async with self._connection() as db:
            async with db.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE motion_id = ? AND round_num = ?
            """, [motion_id, round_num]) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
```

### 3.5 Vote 操作

```python
    # --- Vote CRUD ---
    
    async def add_vote(
        self,
        motion_id: str,
        agent_id: str,
        vote: str,
        confidence: float = 1.0,
        reason: str = None
    ) -> int:
        """添加投票"""
        now = datetime.utcnow().isoformat()
        
        async with self._connection() as db:
            await db.execute("""
                INSERT INTO votes (motion_id, agent_id, vote, 
                                  confidence, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [motion_id, agent_id, vote, confidence, reason, now])
            await db.commit()
            
            async with db.execute("SELECT last_insert_rowid()") as cursor:
                row = await cursor.fetchone()
                return row[0]
    
    async def get_votes(self, motion_id: str) -> list[dict]:
        """获取投票列表"""
        async with self._connection() as db:
            async with db.execute(
                "SELECT * FROM votes WHERE motion_id = ? ORDER BY timestamp",
                [motion_id]
            ) as cursor:
                return [dict(row) async for row in cursor]
    
    async def has_voted(self, motion_id: str, agent_id: str) -> bool:
        """检查是否已投票"""
        async with self._connection() as db:
            async with db.execute("""
                SELECT 1 FROM votes WHERE motion_id = ? AND agent_id = ?
            """, [motion_id, agent_id]) as cursor:
                return await cursor.fetchone() is not None
    
    async def count_votes(self, motion_id: str) -> dict:
        """统计投票"""
        async with self._connection() as db:
            async with db.execute("""
                SELECT vote, COUNT(*) as count FROM votes 
                WHERE motion_id = ? GROUP BY vote
            """, [motion_id]) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}
    
    async def get_vote_summary(self, motion_id: str) -> dict:
        """获取投票汇总（包含权重）"""
        votes = await self.get_votes(motion_id)
        
        summary = {"yes": 0, "no": 0, "abstain": 0, "total": len(votes)}
        
        for vote in votes:
            v = vote["vote"]
            conf = vote.get("confidence", 1.0)
            if v in summary:
                summary[v] += 1
                # 权重计算（可选）
                # summary[f"{v}_weighted"] += conf
        
        return summary
```

### 3.6 统计查询

```python
    # --- 统计查询 ---
    
    async def get_active_motion_count(self) -> int:
        """获取活跃议题数"""
        async with self._connection() as db:
            async with db.execute("""
                SELECT COUNT(*) FROM motions 
                WHERE status IN ('draft', 'discussing', 'voting')
            """) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def get_participant_count(self) -> int:
        """获取参与者数量"""
        async with self._connection() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM agents WHERE is_online = 1"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
```

## 4. 迁移计划

### 4.1 数据库初始化时机

在 Coordinator 服务启动时（lifespan 事件）自动初始化：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    await storage.init_db()
    
    yield
    
    # 关闭时
    pass
```

### 4.2 迁移策略

采用版本化 Schema 管理，支持未来迁移：

```python
SCHEMA_VERSION = 1

SCHEMAS = {
    1: """
    CREATE TABLE IF NOT EXISTS agents (...);
    CREATE TABLE IF NOT EXISTS motions (...);
    CREATE TABLE IF NOT EXISTS messages (...);
    CREATE TABLE IF NOT EXISTS votes (...);
    CREATE INDEX IF NOT EXISTS ...;
    """
}

async def migrate_if_needed(self):
    """检查并执行迁移"""
    async with self._connection() as db:
        # 创建版本表（如果不存在）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT
            )
        """)
        
        # 获取当前版本
        async with db.execute(
            "SELECT MAX(version) FROM schema_version"
        ) as cursor:
            row = await cursor.fetchone()
            current_version = row[0] if row and row[0] else 0
        
        # 应用迁移
        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            if version in SCHEMAS:
                await db.executescript(SCHEMAS[version])
                await db.execute(
                    "INSERT INTO schema_version VALUES (?, ?)",
                    [version, datetime.utcnow().isoformat()]
                )
                await db.commit()
```

### 4.3 备份策略

- 每次服务启动前备份数据库（可选）
- 关键操作使用事务确保原子性
- 定期清理过期数据（可选功能）

## 5. 边界情况处理

### 5.1 并发控制

- 使用 SQLite WAL 模式提高并发读性能
- 写入使用事务包装
- 避免长时间持有锁

```python
# 启用 WAL 模式
await db.execute("PRAGMA journal_mode=WAL")
```

### 5.2 数据完整性

- 外键约束默认启用
- 删除 Motion 时级联删除 messages 和 votes
- UNIQUE 约束防止重复投票

### 5.3 错误处理

```python
async def safe_execute(self, query: str, params: list = None):
    """安全执行 SQL，返回结果或 None"""
    try:
        async with self._connection() as db:
            async with db.execute(query, params or []) as cursor:
                return await cursor.fetchall()
    except aiosqlite.Error as e:
        logger.error(f"Database error: {e}")
        return None
```

### 5.4 边界检查

- Motion 状态转换前验证合法性
- 投票前检查是否已投票
- 发言前检查是否在讨论状态
- 轮次增加前检查是否完成当前轮

## 6. 实现文件结构

```
coordinator/
├── __init__.py
├── main.py
├── config.py
├── models.py
├── storage.py          # 本设计文档的实现
├── router.py
├── ws.py
└── state.py
```

## 7. 依赖

```python
# requirements.txt
aiosqlite>=0.19.0
pydantic>=2.0.0
```

## 8. 测试计划

1. 单元测试：各 CRUD 方法
2. 集成测试：状态机 + 存储层
3. 并发测试：多 Agent 同时投票
4. 迁移测试：版本升级