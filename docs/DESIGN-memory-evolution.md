# Phase 3: Memory and Evolution Design

## 概述

设计 Agora 的记忆和进化机制：讨论结论自动持久化、历史模式学习、参与者判断准确性追踪、相似主题自动引用。

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Hermes Memory                          │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ discussion_mem/ │  │ judgment_acc/   │                  │
│  │   conclusions   │  │  agent_scores   │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
           ▲                    ▲                    ▲
           │                    │                    │
    ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
    │ memory_sync │      │  history    │      │  evaluator  │
    │   .py       │      │  pattern    │      │  tracker    │
    └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
           │                    │                    │
    ┌──────┴────────────────────┴────────────────────┴──────┐
    │                   Coordinator                          │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
    │  │  motions    │  │   votes     │  │ assessments │   │
    │  └─────────────┘  └─────────────┘  └─────────────┘   │
    └────────────────────────────────────────────────────────┘
```

## 2. 核心模块设计

### 2.1 Memory Sync 模块

将讨论结果写入 Hermes memory。

```python
# coordinator/memory_sync.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json
import aiosqlite


@dataclass
class DiscussionConclusion:
    """讨论结论数据结构"""
    motion_id: str
    title: str
    decision: str  # adopted/rejected/no_consensus
    rationale: str
    key_points: list[str]
    action_items: list[str]
    participants: list[str]
    voting_method: str
    votes_summary: dict
    created_at: str


class MemorySync:
    """讨论结论同步到 Hermes Memory"""

    def __init__(self, storage, memory_path: str = "~/.hermes/memories"):
        self.storage = storage
        self.memory_path = memory_path

    async def sync_conclusion(self, motion_id: str) -> bool:
        """同步讨论结论到 Hermes memory"""
        # 1. 获取完整讨论数据
        motion = await self.storage.get_motion(motion_id)
        if not motion or motion.get("status") != "closed":
            return False

        votes = await self.storage.get_votes(motion_id)
        messages = await self.storage.get_messages(motion_id)

        # 2. 构建结论对象
        conclusion = DiscussionConclusion(
            motion_id=motion["id"],
            title=motion["title"],
            decision=motion.get("decision", "no_consensus"),
            rationale=motion.get("rationale", ""),
            key_points=self._extract_key_points(messages),
            action_items=json.loads(motion.get("action_items", "[]")),
            participants=list(set(m.get("agent_id") for m in messages)),
            voting_method=motion.get("voting_method", "simple_majority"),
            votes_summary=self._summarize_votes(votes),
            created_at=motion.get("closed_at", datetime.utcnow().isoformat())
        )

        # 3. 写入 Hermes memory 格式
        await self._write_to_memory(conclusion)
        return True

    async def _write_to_memory(self, conclusion: DiscussionConclusion) -> None:
        """写入 memory 文件"""
        import os
        from pathlib import Path

        memory_dir = Path(self.memory_path).expanduser() / "discussion_conclusions"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # 按年月组织：2026/06/conclusion_uuid.json
        dt = datetime.fromisoformat(conclusion.created_at)
        month_dir = memory_dir / str(dt.year) / f"{dt.month:02d}"
        month_dir.mkdir(parents=True, exist_ok=True)

        file_path = month_dir / f"{conclusion.motion_id}.json"
        
        content = {
            "type": "agora_conclusion",
            "motion_id": conclusion.motion_id,
            "title": conclusion.title,
            "decision": conclusion.decision,
            "rationale": conclusion.rationale,
            "key_points": conclusion.key_points,
            "action_items": conclusion.action_items,
            "participants": conclusion.participants,
            "voting_method": conclusion.voting_method,
            "votes_summary": conclusion.votes_summary,
            "tags": self._generate_tags(conclusion),
            "timestamp": conclusion.created_at
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    def _generate_tags(self, conclusion: DiscussionConclusion) -> list[str]:
        """生成标签用于相似主题检索"""
        tags = [conclusion.decision, conclusion.voting_method]
        # 从标题提取关键词作为标签
        words = conclusion.title.lower().split()
        tags.extend([w for w in words if len(w) > 2][:5])
        return tags

    def _extract_key_points(self, messages: list[dict]) -> list[str]:
        """提取关键论点（简化版：取前5个长发言的观点）"""
        sorted_msgs = sorted(
            [m for m in messages if len(m.get("content", "")) > 50],
            key=lambda m: len(m.get("content", "")),
            reverse=True
        )
        return [m.get("content", "")[:200] for m in sorted_msgs[:5]]

    def _summarize_votes(self, votes: list[dict]) -> dict:
        """汇总投票"""
        summary = {}
        for v in votes:
            vote = v.get("vote", "abstain")
            summary[vote] = summary.get(vote, 0) + 1
        return summary
```

### 2.2 历史决策模式模块

Coordinator 记住历史决策模式，用于优化讨论策略。

```python
# coordinator/history_pattern.py

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict


@dataclass
class DecisionPattern:
    """决策模式"""
    topic_category: str
    decision: str
    avg_rounds: float
    consensus_level: str
    common_arguments: list[str] = field(default_factory=list)


class HistoryPattern:
    """历史决策模式分析"""

    def __init__(self, storage, db_path: str):
        self.storage = storage
        self.db_path = db_path
        self._pattern_cache: dict = {}
        self._cache_loaded = False

    async def load_patterns(self) -> None:
        """从数据库加载历史模式"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # 加载已关闭的 motion 作为历史
            async with db.execute("""
                SELECT * FROM motions 
                WHERE status = 'closed' AND decision IS NOT NULL
                ORDER BY closed_at DESC
                LIMIT 100
            """) as cursor:
                rows = await cursor.fetchall()
                
        patterns_by_topic = defaultdict(list)
        for row in rows:
            topic = self._categorize_topic(row["title"])
            patterns_by_topic[topic].append(dict(row))
        
        self._pattern_cache = dict(patterns_by_topic)
        self._cache_loaded = True

    def _categorize_topic(self, title: str) -> str:
        """简单主题分类（可用 NLP 扩展）"""
        title_lower = title.lower()
        
        categories = {
            "architecture": ["架构", "microservice", "service", "design", "系统设计"],
            "priority": ["优先级", "priority", "重要", "紧急"],
            "resource": ["资源", "resource", "预算", "成本", "人力"],
            "process": ["流程", "process", "方法", "规范"],
            "tooling": ["工具", "tool", "框架", "library"],
        }
        
        for cat, keywords in categories.items():
            if any(kw in title_lower for kw in keywords):
                return cat
        return "other"

    async def get_pattern(self, topic: str) -> Optional[DecisionPattern]:
        """获取主题的决策模式"""
        if not self._cache_loaded:
            await self.load_patterns()
        
        category = self._categorize_topic(topic)
        history = self._pattern_cache.get(category, [])
        
        if not history:
            return None
        
        # 统计分析
        decisions = [m.get("decision") for m in history if m.get("decision")]
        rounds = [m.get("rounds", 3) for m in history]
        
        return DecisionPattern(
            topic_category=category,
            decision=max(set(decisions), key=decisions.count) if decisions else "no_consensus",
            avg_rounds=sum(rounds) / len(rounds) if rounds else 3.0,
            consensus_level=self._calc_consensus_level(history),
            common_arguments=self._extract_common_args(history)
        )

    def _calc_consensus_level(self, history: list[dict]) -> str:
        """计算共识级别"""
        # 简化版：根据 yes 票比例
        yes_ratios = []
        for h in history:
            votes = json.loads(h.get("action_items", "[]"))  # 复用字段存投票汇总
            if votes:
                total = sum(votes.values())
                yes = votes.get("yes", 0)
                yes_ratios.append(yes / total if total > 0 else 0)
        
        if not yes_ratios:
            return "unknown"
        
        avg = sum(yes_ratios) / len(yes_ratios)
        if avg >= 0.7:
            return "high"
        elif avg >= 0.5:
            return "moderate"
        else:
            return "low"

    def _extract_common_args(self, history: list[dict]) -> list[str]:
        """提取常见论点"""
        # 简化版：从 rationale 提取
        return []

    async def suggest_strategy(self, topic: str) -> dict:
        """基于历史模式建议讨论策略"""
        pattern = await self.get_pattern(topic)
        
        if not pattern:
            return {"strategy": "standard", "reason": "无历史数据"}
        
        strategy = {
            "strategy": "standard",
            "suggested_rounds": int(pattern.avg_rounds),
            "expected_consensus": pattern.consensus_level,
            "recommendations": []
        }
        
        # 根据历史调整策略
        if pattern.consensus_level == "high":
            strategy["strategy"] = "fast_track"
            strategy["recommendations"].append("历史显示容易达成共识，可提前投票")
        elif pattern.consensus_level == "low":
            strategy["strategy"] = "deep_discussion"
            strategy["recommendations"].append("历史显示分歧较大，建议引入更多论证")
        
        return strategy
```

### 2.3 参与者判断准确性追踪

追踪每个 Agent 的投票准确性（预测 vs 结果）。

```python
# coordinator/judgment_tracker.py

from dataclasses import dataclass, field
from typing import Optional
import aiosqlite
from datetime import datetime


@dataclass
class AgentScore:
    """Agent 判断准确性得分"""
    agent_id: str
    total_decisions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    avg_confidence: float = 0.0
    recent_trend: list[float] = field(default_factory=list)  # 最近5次准确性


class JudgmentTracker:
    """参与者判断准确性追踪器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._score_cache: dict[str, AgentScore] = {}

    async def record_vote(self, motion_id: str, agent_id: str, 
                          predicted_outcome: str, actual_outcome: str,
                          confidence: float) -> None:
        """记录一次投票预测"""
        is_correct = 1 if predicted_outcome == actual_outcome else 0
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO judgment_records 
                (motion_id, agent_id, predicted, actual, confidence, is_correct, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (motion_id, agent_id, predicted_outcome, actual_outcome, 
                  confidence, is_correct, datetime.utcnow().isoformat()))
            await db.commit()
        
        # 更新缓存
        await self._update_cache(agent_id)

    async def get_agent_score(self, agent_id: str) -> AgentScore:
        """获取 Agent 的准确性得分"""
        if agent_id in self._score_cache:
            return self._score_cache[agent_id]
        
        await self._update_cache(agent_id)
        return self._score_cache.get(agent_id, AgentScore(agent_id=agent_id))

    async def _update_cache(self, agent_id: str) -> None:
        """更新缓存"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 统计正确预测数
            async with db.execute("""
                SELECT COUNT(*) as total, 
                       SUM(is_correct) as correct,
                       AVG(confidence) as avg_conf
                FROM judgment_records 
                WHERE agent_id = ?
            """, (agent_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row or row["total"] == 0:
                self._score_cache[agent_id] = AgentScore(agent_id=agent_id)
                return
            
            total = row["total"]
            correct = row["correct"] or 0
            accuracy = correct / total if total > 0 else 0.0
            
            # 获取最近5次趋势
            async with db.execute("""
                SELECT is_correct FROM judgment_records 
                WHERE agent_id = ?
                ORDER BY recorded_at DESC
                LIMIT 5
            """, (agent_id,)) as cursor:
                rows = await cursor.fetchall()
            
            recent = [r["is_correct"] for r in rows]
            
            self._score_cache[agent_id] = AgentScore(
                agent_id=agent_id,
                total_decisions=total,
                correct_predictions=correct,
                accuracy=accuracy,
                avg_confidence=row["avg_conf"] or 0.0,
                recent_trend=recent
            )

    async def get_weighted_vote(self, agent_id: str) -> float:
        """获取 Agent 的投票权重（基于准确性）"""
        score = await self.get_agent_score(agent_id)
        
        if score.total_decisions < 3:
            return 1.0  # 新 Agent 默认权重
        
        # 准确性越高权重越高
        return 0.5 + (score.accuracy * 0.5)  # 0.5 - 1.0

    async def get_leaderboard(self, limit: int = 10) -> list[AgentScore]:
        """获取准确性排名"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT agent_id, 
                       COUNT(*) as total,
                       SUM(is_correct) as correct
                FROM judgment_records 
                GROUP BY agent_id
                ORDER BY correct DESC, total DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
        
        results = []
        for row in rows:
            total = row["total"]
            correct = row["correct"] or 0
            results.append(AgentScore(
                agent_id=row["agent_id"],
                total_decisions=total,
                correct_predictions=correct,
                accuracy=correct / total if total > 0 else 0.0
            ))
        
        return results
```

### 2.4 相似主题检测模块

检测新议题是否与历史结论相似，自动引用。

```python
# coordinator/similar_topic.py

from typing import Optional
import re
from collections import Counter


class SimilarTopicDetector:
    """相似主题检测器"""

    def __init__(self, memory_path: str = "~/.hermes/memories/discussion_conclusions"):
        self.memory_path = memory_path
        self._index: dict = {}

    async def find_similar(self, title: str, threshold: float = 0.6) -> list[dict]:
        """查找相似主题"""
        title_keywords = self._extract_keywords(title)
        
        similar = []
        for category, conclusions in self._load_conclusions().items():
            for conclusion in conclusions:
                score = self._calculate_similarity(
                    title_keywords, 
                    conclusion.get("tags", [])
                )
                
                if score >= threshold:
                    similar.append({
                        "motion_id": conclusion["motion_id"],
                        "title": conclusion["title"],
                        "decision": conclusion["decision"],
                        "rationale": conclusion["rationale"],
                        "similarity": score,
                        "key_points": conclusion.get("key_points", [])[:3]
                    })
        
        # 按相似度排序
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:5]

    def _extract_keywords(self, text: str) -> set[str]:
        """提取关键词"""
        # 简单分词
        words = re.findall(r'\w+', text.lower())
        # 过滤停用词
        stopwords = {"the", "a", "an", "is", "are", "was", "were", 
                     "of", "in", "on", "at", "to", "for", "和", "的", "是"}
        return set(w for w in words if len(w) > 2 and w not in stopwords)

    def _calculate_similarity(self, keywords1: set, tags: list) -> float:
        """计算相似度"""
        if not keywords1 or not tags:
            return 0.0
        
        tag_set = set(t.lower() for t in tags if isinstance(t, str))
        
        intersection = len(keywords1 & tag_set)
        union = len(keywords1 | tag_set)
        
        return intersection / union if union > 0 else 0.0

    def _load_conclusions(self) -> dict:
        """加载历史结论（带缓存）"""
        if self._index:
            return self._index
        
        import os
        from pathlib import Path
        from datetime import datetime
        
        conclusions_by_tag = {}
        
        memory_dir = Path(self.memory_path).expanduser()
        if not memory_dir.exists():
            return {}
        
        # 遍历所有结论文件
        for year_dir in memory_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for file in month_dir.glob("*.json"):
                    try:
                        import json
                        with open(file) as f:
                            data = json.load(f)
                        
                        tags = data.get("tags", [])
                        for tag in tags:
                            if tag not in conclusions_by_tag:
                                conclusions_by_tag[tag] = []
                            conclusions_by_tag[tag].append(data)
                    except:
                        continue
        
        self._index = conclusions_by_tag
        return conclusions_by_tag

    async def generate_reference_context(self, title: str) -> str:
        """生成引用上下文"""
        similar = await self.find_similar(title)
        
        if not similar:
            return ""
        
        lines = ["【相关历史结论】"]
        for s in similar[:3]:
            lines.append(f"- {s['title']}: {s['decision']} (相似度 {s['similarity']:.0%})")
            if s.get("rationale"):
                lines.append(f"  理由: {s['rationale'][:100]}...")
        
        return "\n".join(lines)
```

### 2.5 Curator 优化器

综合历史模式和判断准确性，优化讨论策略。

```python
# coordinator/curator.py

from typing import Optional
from .history_pattern import HistoryPattern
from .judgment_tracker import JudgmentTracker
from .similar_topic import SimilarTopicDetector


class DiscussionCurator:
    """讨论策略优化器"""

    def __init__(self, storage, db_path: str, memory_path: str):
        self.storage = storage
        self.history_pattern = HistoryPattern(storage, db_path)
        self.judgment_tracker = JudgmentTracker(db_path)
        self.similar_detector = SimilarTopicDetector(memory_path)

    async def optimize_motion(self, motion: dict) -> dict:
        """优化议题配置"""
        title = motion.get("title", "")
        
        # 1. 获取历史模式建议
        strategy = await self.history_pattern.suggest_strategy(title)
        
        # 2. 查找相似历史结论
        reference_context = await self.similar_detector.generate_reference_context(title)
        
        # 3. 调整配置
        optimized = {
            **motion,
            "suggested_rounds": strategy.get("suggested_rounds", motion.get("rounds", 3)),
            "strategy": strategy.get("strategy", "standard"),
            "reference_context": reference_context,
            "recommendations": strategy.get("recommendations", [])
        }
        
        # 4. 如果有高准确性参与者，标记用于加权投票
        if strategy.get("expected_consensus") == "low":
            top_performers = await self.judgment_tracker.get_leaderboard(3)
            optimized["weighted_voters"] = [p.agent_id for p in top_performers]
        
        return optimized

    async def post_discussion_review(self, motion_id: str) -> dict:
        """讨论后复盘"""
        motion = await self.storage.get_motion(motion_id)
        votes = await self.storage.get_votes(motion_id)
        
        # 记录每个参与者的预测准确性
        actual_decision = motion.get("decision")
        
        for vote in votes:
            await self.judgment_tracker.record_vote(
                motion_id=motion_id,
                agent_id=vote["agent_id"],
                predicted_outcome=vote["vote"],
                actual_outcome=actual_decision,
                confidence=vote.get("confidence", 1.0)
            )
        
        return {
            "motion_id": motion_id,
            "decision": actual_decision,
            "participants_evaluated": len(votes)
        }
```

## 3. 数据库扩展

```sql
-- judgment_records 表：记录投票预测准确性
CREATE TABLE IF NOT EXISTS judgment_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    predicted TEXT NOT NULL,
    actual TEXT NOT NULL,
    confidence REAL,
    is_correct INTEGER,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_judgment_agent ON judgment_records(agent_id);
```

## 4. 集成到 Coordinator

在讨论结束时触发记忆同步：

```python
# coordinator/router.py 或 state.py 扩展

async def close_motion(motion_id: str, storage: Storage) -> None:
    """关闭议题并同步记忆"""
    # 原有逻辑：更新状态、记录结果
    
    # Phase 3: 同步到 Hermes memory
    memory_sync = MemorySync(storage)
    await memory_sync.sync_conclusion(motion_id)
    
    # Phase 3: 更新判断准确性
    curator = DiscussionCurator(storage, db_path, memory_path)
    await curator.post_discussion_review(motion_id)
```

创建新议题时自动优化：

```python
async def create_motion(request: MotionCreateRequest) -> Motion:
    """创建议题并优化"""
    # 原有逻辑
    
    # Phase 3: Curator 优化
    curator = DiscussionCurator(storage, db_path, memory_path)
    optimized = await curator.optimize_motion(motion.dict())
    
    return Motion(**optimized)
```

## 5. 实现任务分解

| 任务 | 文件 | 描述 | 预估行数 |
|------|------|------|----------|
| P3-1 | `coordinator/memory_sync.py` | 讨论结论写入 Hermes memory | ~120 |
| P3-2 | `coordinator/history_pattern.py` | 历史决策模式分析 | ~100 |
| P3-3 | `coordinator/judgment_tracker.py` | 参与者判断准确性追踪 | ~100 |
| P3-4 | `coordinator/similar_topic.py` | 相似主题检测 | ~80 |
| P3-5 | `coordinator/curator.py` | Curator 优化器 | ~60 |
| P3-6 | `coordinator/storage/schema.py` | 新增 judgment_records 表 | +20 |
| P3-7 | `coordinator/storage/judgments.py` | judgment_records CRUD | ~60 |

总计：~540 行代码，7 个子任务