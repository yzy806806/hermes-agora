# Phase 2: Smart Discussion Design

## 概述

设计智能讨论机制：不再是固定 N 轮机械轮次，而是根据讨论质量动态调整。Coordinator 作为讨论主持人，评估讨论充分性并做出决策。

## 1. 智能讨论评估器

### 1.1 评估维度

Coordinator 在每轮结束后评估讨论质量：

```python
# coordinator/assessment.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
from .models import Stance

class ConsensusLevel(str, Enum):
    """共识级别"""
    HIGH = "high"        # 高度共识
    MODERATE = "moderate" # 中度共识
    LOW = "low"          # 低度共识
    FRACTURED = "fractured"  # 严重分裂

class AssessmentResult(str, Enum):
    """评估结果"""
    CONSENSUS_REACHED = "consensus_reached"  # 达成共识，可提前投票
    SUFFICIENT = "sufficient"                # 讨论充分，可投票
    NEEDS_MORE = "needs_more"                # 需要继续讨论
    OFF_TOPIC = "off_topic"                  # 偏离主题
    DEVILS_ADVOCATE = "devils_advocate"      # 需要引入反对意见

@dataclass
class DiscussionMetrics:
    """讨论指标"""
    total_messages: int
    stance_distribution: Dict[Stance, int]
    argument_quality_score: float  # 0.0-1.0
    topic_relevance_score: float   # 0.0-1.0
    key_points_identified: List[str]
    unresolved_points: List[str]
    
@dataclass
class Assessment:
    """评估结果"""
    result: AssessmentResult
    consensus_level: ConsensusLevel
    metrics: DiscussionMetrics
    rationale: str
    recommendations: List[str]
```

### 1.2 共识检测算法

```python
class ConsensusDetector:
    """共识检测器"""
    
    def detect(self, messages: List[dict]) -> tuple[ConsensusLevel, Dict[Stance, int]]:
        """检测共识级别"""
        if not messages:
            return ConsensusLevel.LOW, {}
        
        # 统计立场分布
        stance_counts = {}
        for msg in messages:
            stance = msg.get("stance")
            stance_counts[stance] = stance_counts.get(stance, 0) + 1
        
        total = sum(stance_counts.values())
        if total == 0:
            return ConsensusLevel.LOW, {}
        
        # 计算各立场比例
        support_ratio = stance_counts.get(Stance.SUPPORT, 0) / total
        oppose_ratio = stance_counts.get(Stance.OPPOSE, 0) / total
        neutral_ratio = stance_counts.get(Stance.NEUTRAL, 0) / total
        
        # 判断共识级别
        if support_ratio >= 0.7:
            return ConsensusLevel.HIGH, stance_counts
        elif support_ratio >= 0.5 or oppose_ratio >= 0.5:
            return ConsensusLevel.MODERATE, stance_counts
        elif support_ratio > 0.3 and oppose_ratio > 0.3:
            return ConsensusLevel.FRACTURED, stance_counts
        else:
            return ConsensusLevel.LOW, stance_counts
```

### 1.3 讨论质量评估

```python
class QualityAssessor:
    """讨论质量评估器"""
    
    def __init__(self, llm_endpoint: str = None):
        self.llm_endpoint = llm_endpoint
    
    async def assess(self, motion_id: str, storage: Storage) -> Assessment:
        """评估讨论质量"""
        messages = await storage.get_messages(motion_id)
        motion = await storage.get_motion(motion_id)
        
        # 1. 检测共识级别
        consensus_detector = ConsensusDetector()
        consensus_level, stance_counts = consensus_detector.detect(messages)
        
        # 2. 评估论点质量（简化版：检查发言长度、论据数量）
        quality_score = self._assess_argument_quality(messages)
        
        # 3. 评估主题相关性（简化版：检查关键词）
        relevance_score = self._assess_topic_relevance(messages, motion.title)
        
        # 4. 识别关键点和未解决分歧
        key_points = self._extract_key_points(messages)
        unresolved = self._identify_unresolved(messages)
        
        metrics = DiscussionMetrics(
            total_messages=len(messages),
            stance_distribution=stance_counts,
            argument_quality_score=quality_score,
            topic_relevance_score=relevance_score,
            key_points_identified=key_points,
            unresolved_points=unresolved
        )
        
        # 5. 综合评估决策
        return self._make_decision(consensus_level, metrics, len(messages))
    
    def _assess_argument_quality(self, messages: List[dict]) -> float:
        """评估论点质量"""
        if not messages:
            return 0.0
        
        total_evidence = sum(
            len(msg.get("evidence", [])) 
            for msg in messages
        )
        
        avg_length = sum(
            len(msg.get("content", "")) 
            for msg in messages
        ) / len(messages)
        
        # 简单的质量评分
        evidence_score = min(total_evidence / len(messages), 1.0)
        length_score = min(avg_length / 200, 1.0)
        
        return (evidence_score * 0.6 + length_score * 0.4)
    
    def _assess_topic_relevance(self, messages: List[dict], topic: str) -> float:
        """评估主题相关性"""
        # 简化版：检查是否包含主题关键词
        # 实际可用 NLP 或 LLM 判断
        return 0.8  # 占位
    
    def _extract_key_points(self, messages: List[dict]) -> List[str]:
        """提取关键论点"""
        # 简化版：返回立场分布
        return []
    
    def _identify_unresolved(self, messages: List[dict]) -> List[str]:
        """识别未解决分歧"""
        # 简化版
        return []
    
    def _make_decision(
        self, 
        consensus_level: ConsensusLevel, 
        metrics: DiscussionMetrics,
        message_count: int
    ) -> Assessment:
        """做出评估决策"""
        min_messages = 6  # 最小发言数
        
        # 规则1: 高度共识 → 提前投票
        if consensus_level == ConsensusLevel.HIGH:
            return Assessment(
                result=AssessmentResult.CONSENSUS_REACHED,
                consensus_level=consensus_level,
                metrics=metrics,
                rationale="检测到高度共识，支持方占多数",
                recommendations=["提前进入投票阶段"]
            )
        
        # 规则2: 严重分裂 + 质量低 → 需要更多讨论
        if consensus_level == ConsensusLevel.FRACTURED:
            if metrics.argument_quality_score < 0.5:
                return Assessment(
                    result=AssessmentResult.NEEDS_MORE,
                    consensus_level=consensus_level,
                    metrics=metrics,
                    rationale="分歧严重且论据不足，需要更多讨论",
                    recommendations=["继续讨论", "引入更多论据"]
                )
        
        # 规则3: 主题相关度低 → 拉回正题
        if metrics.topic_relevance_score < 0.5:
            return Assessment(
                result=AssessmentResult.OFF_TOPIC,
                consensus_level=consensus_level,
                metrics=metrics,
                rationale="讨论偏离主题",
                recommendations=["重新聚焦主题", "跳过无关讨论"]
            )
        
        # 规则4: 发言数足够且质量足够 → 可以投票
        if message_count >= min_messages and metrics.argument_quality_score >= 0.5:
            return Assessment(
                result=AssessmentResult.SUFFICIENT,
                consensus_level=consensus_level,
                metrics=metrics,
                rationale="讨论已充分",
                recommendations=["进入投票阶段"]
            )
        
        # 规则5: 需要更多讨论
        return Assessment(
            result=AssessmentResult.NEEDS_MORE,
            consensus_level=consensus_level,
            metrics=metrics,
            rationale="讨论尚未充分",
            recommendations=["继续下一轮"]
        )
```

## 2. 智能讨论调度器

### 2.1 扩展状态机

```python
# 在 state.py 中扩展

class SmartDiscussionState(str, Enum):
    """智能讨论状态"""
    DRAFT = "draft"
    DISCUSSING = "discussing"
    ASSESSING = "assessing"      # 新增：评估中
    DEVILS_ADVOCATE = "devils_advocate"  # 新增：魔鬼代言人
    VOTING = "voting"
    CLOSED = "closed"

class SmartStateMachine(StateMachine):
    """智能讨论状态机"""
    
    async def transition(self, motion_id: str, event: str) -> SmartDiscussionState:
        """状态转换"""
        # ... 现有逻辑 ...
        
        # 新增转换
        if old_status == SmartDiscussionState.DISCUSSING and event == "assess":
            new_status = SmartDiscussionState.ASSESSING
        elif old_status == SmartDiscussionState.ASSESSING and event == "needs_devils_advocate":
            new_status = SmartDiscussionState.DEVILS_ADVOCATE
        elif old_status == SmartDiscussionState.DEVILS_ADVOCATE and event == "devils_advocate_done":
            new_status = SmartDiscussionState.DISCUSSING
        
        return new_status
```

### 2.2 智能调度器

```python
# coordinator/discuss.py 扩展

class SmartDiscussionScheduler(DiscussionScheduler):
    """智能讨论调度器"""
    
    def __init__(self, storage: Storage, ws_manager: ConnectionManager, config: Settings):
        super().__init__(storage, ws_manager)
        self.config = config
        self.quality_assessor = QualityAssessor()
        self.consensus_detector = ConsensusDetector()
        self.devils_advocate_enabled = config.devils_advocate_enabled
        self.max_rounds = config.default_rounds
    
    async def request_next_speak(self, motion_id: str) -> None:
        """请求下一个发言（智能版）"""
        motion = await self.storage.get_motion(motion_id)
        current_round = motion.current_round
        
        # 检查是否需要进行评估
        if await self._should_assess(motion_id, current_round):
            await self._run_assessment(motion_id)
            return
        
        # 原有逻辑：继续轮次
        await super().request_next_speak(motion_id)
    
    async def _should_assess(self, motion_id: str, current_round: int) -> bool:
        """检查是否需要评估"""
        # 每轮结束后评估
        messages = await self.storage.get_messages(motion_id)
        current_round_messages = [m for m in messages if m.get("round") == current_round]
        
        # 如果当前轮所有 Agent 都已发言
        agents = await self.storage.list_agents()
        spoken_agents = set(m.get("agent_id") for m in current_round_messages)
        
        return len(spoken_agents) >= len(agents)
    
    async def _run_assessment(self, motion_id: str) -> None:
        """运行评估并决策"""
        assessment = await self.quality_assessor.assess(motion_id, self.storage)
        
        # 广播评估结果
        await self.ws_manager.broadcast({
            "type": "ASSESSMENT",
            "motion_id": motion_id,
            "payload": {
                "result": assessment.result,
                "consensus_level": assessment.consensus_level,
                "metrics": {
                    "total_messages": assessment.metrics.total_messages,
                    "argument_quality": assessment.metrics.argument_quality_score,
                    "topic_relevance": assessment.metrics.topic_relevance_score,
                },
                "rationale": assessment.rationale,
                "recommendations": assessment.recommendations
            }
        })
        
        # 根据评估结果行动
        if assessment.result == AssessmentResult.CONSENSUS_REACHED:
            await self.transition_to_voting(motion_id)
        elif assessment.result == AssessmentResult.SUFFICIENT:
            await self.transition_to_voting(motion_id)
        elif assessment.result == AssessmentResult.OFF_TOPIC:
            await self._redirect_discussion(motion_id, assessment)
        elif assessment.result == AssessmentResult.DEVILS_ADVOCATE:
            await self._trigger_devils_advocate(motion_id)
        else:  # NEEDS_MORE
            await self._continue_to_next_round(motion_id)
    
    async def _redirect_discussion(self, motion_id: str, assessment: Assessment) -> None:
        """重定向讨论"""
        motion = await self.storage.get_motion(motion_id)
        
        await self.ws_manager.broadcast({
            "type": "TOPIC_REDIRECT",
            "motion_id": motion_id,
            "payload": {
                "message": "讨论偏离主题，请聚焦于：",
                "focus_areas": assessment.metrics.key_points_identified[:3],
                "unresolved_points": assessment.metrics.unresolved_points[:3]
            }
        })
        
        # 继续讨论但带话题引导
        await self._continue_to_next_round(motion_id)
    
    async def _trigger_devils_advocate(self, motion_id: str) -> None:
        """触发魔鬼代言人"""
        # 见下一节
        pass
    
    async def _continue_to_next_round(self, motion_id: str) -> None:
        """继续下一轮"""
        motion = await self.storage.get_motion(motion_id)
        
        if motion.current_round >= self.max_rounds:
            # 达到最大轮次，强制进入投票
            await self.transition_to_voting(motion_id)
        else:
            await self.storage.update_motion_round(motion_id, motion.current_round + 1)
            await self.ws_manager.broadcast({
                "type": "ROUND_COMPLETE",
                "motion_id": motion_id,
                "payload": {"round": motion.current_round, "next_round": motion.current_round + 1}
            })
            await self.request_next_speak(motion_id)
```

## 3. 魔鬼代言人机制

### 3.1 设计原理

当讨论呈现一边倒趋势时，Coordinator 强制要求某个 Agent 提出反对意见，确保讨论全面性。

```python
# coordinator/devils_advocate.py

from typing import Optional
from dataclasses import dataclass

@dataclass
class DevilsAdvocateConfig:
    """魔鬼代言人配置"""
    enabled: bool = True
    trigger_threshold: float = 0.7  # 支持率超过 70% 触发
    max_triggers_per_motion: int = 2  # 最多触发2次
    force_oppose_weight: float = 0.3  # 反对意见权重

class DevilsAdvocateManager:
    """魔鬼代言人管理器"""
    
    def __init__(self, storage: Storage, config: DevilsAdvocateConfig):
        self.storage = storage
        self.config = config
        self.trigger_count: Dict[str, int] = {}  # motion_id -> count
    
    async def should_trigger(self, motion_id: str) -> tuple[bool, Optional[str]]:
        """判断是否应该触发魔鬼代言人"""
        if not self.config.enabled:
            return False, None
        
        # 检查触发次数
        count = self.trigger_count.get(motion_id, 0)
        if count >= self.config.max_triggers_per_motion:
            return False, None
        
        # 检测立场分布
        messages = await self.storage.get_messages(motion_id)
        if len(messages) < 3:
            return False, None
        
        stance_counts = {}
        for msg in messages:
            stance = msg.get("stance")
            stance_counts[stance] = stance_counts.get(stance, 0) + 1
        
        total = sum(stance_counts.values())
        support_ratio = stance_counts.get(Stance.SUPPORT, 0) / total
        
        if support_ratio >= self.config.trigger_threshold:
            # 需要找一个未发言反对的 Agent
            oppose_agents = {m["agent_id"] for m in messages if m.get("stance") == Stance.OPPOSE}
            all_agents = {a.agent_id for a in await self.storage.list_agents()}
            potential_agents = all_agents - oppose_agents
            
            if potential_agents:
                return True, list(potential_agents)[0]
        
        return False, None
    
    async def trigger(self, motion_id: str, target_agent_id: str) -> None:
        """触发魔鬼代言人"""
        self.trigger_count[motion_id] = self.trigger_count.get(motion_id, 0) + 1
        
        motion = await self.storage.get_motion(motion_id)
        
        # 发送特殊请求
        await ws_manager.send(target_agent_id, {
            "type": "DEVILS_ADVOCATE_REQUEST",
            "motion_id": motion_id,
            "payload": {
                "round": motion.current_round + 1,
                "topic": motion.title,
                "description": motion.description,
                "instruction": "请从反对角度提出你的观点和质疑，确保讨论的全面性。"
            }
        })
```

### 3.2 WebSocket 消息扩展

```python
# models.py 扩展

class MessageType(str, Enum):
    # ... 现有 ...
    ASSESSMENT = "ASSESSMENT"
    TOPIC_REDIRECT = "TOPIC_REDIRECT"
    DEVILS_ADVOCATE_REQUEST = "DEVILS_ADVOCATE_REQUEST"
    DEVILS_ADVOCATE_RESPONSE = "DEVILS_ADVOCATE_RESPONSE"
```

## 4. 分歧点聚焦

### 4.1 设计原理

只聚焦讨论尚未达成共识的点，跳过已解决的问题。

```python
# coordinator/focus.py

class DisagreementFocus:
    """分歧点聚焦器"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    async def identify_unresolved_points(self, motion_id: str) -> List[str]:
        """识别未解决的分歧点"""
        messages = await self.storage.get_messages(motion_id)
        
        # 按立场分组消息
        by_stance: Dict[Stance, List[dict]] = {
            Stance.SUPPORT: [],
            Stance.OPPOSE: [],
            Stance.NEUTRAL: []
        }
        
        for msg in messages:
            stance = msg.get("stance")
            if stance in by_stance:
                by_stance[stance].append(msg)
        
        # 如果某立场只有少数发言，标记为需要更多讨论
        total = sum(len(v) for v in by_stance.values())
        if total == 0:
            return []
        
        unresolved = []
        for stance, msgs in by_stance.items():
            if len(msgs) / total < 0.2:
                unresolved.append(f"需要更多{stance.value}观点")
        
        return unresolved
    
    async def generate_focus_prompt(self, motion_id: str) -> str:
        """生成聚焦提示"""
        unresolved = await self.identify_unresolved_points(motion_id)
        
        if not unresolved:
            return "请继续讨论，提出你的最终观点。"
        
        return f"当前讨论存在以下分歧点，请重点讨论：\n" + "\n".join(
            f"- {p}" for p in unresolved
        )
```

### 4.2 状态存储扩展

```python
# storage/schema.sql 扩展

ALTER TABLE motions ADD COLUMN assessment_config TEXT;
ALTER TABLE motions ADD COLUMN devils_advocate_count INTEGER DEFAULT 0;
ALTER TABLE motions ADD COLUMN focus_areas TEXT;
```

## 5. 接口变更

### 5.1 新增配置项

```python
# config.py 扩展

class Settings(BaseSettings):
    # ... 现有 ...
    
    # 智能讨论配置
    smart_discussion_enabled: bool = True
    devils_advocate_enabled: bool = True
    max_rounds: int = 5
    min_messages_for_early_vote: int = 6
    
    # 评估配置
    consensus_threshold_high: float = 0.7
    consensus_threshold_moderate: float = 0.5
```

### 5.2 新增 API

```python
# router.py 扩展

@router.get("/motions/{motion_id}/assessment")
async def get_assessment(motion_id: str):
    """获取当前讨论的评估结果"""
    # 需要实现评估结果缓存
    return {"assessment": "..."}

@router.post("/motions/{motion_id}/force-vote")
async def force_vote(motion_id: str):
    """强制提前投票"""
    await smart_scheduler.transition_to_voting(motion_id)
    return {"status": "voting_started"}
```

## 6. 数据模型变更

### 6.1 Motion 扩展

```python
# models.py 扩展

class Motion(BaseModel):
    # ... 现有 ...
    
    # Phase 2 新增
    smart_mode: bool = True
    assessment_config: Optional[Dict] = None
    devils_advocate_count: int = 0
    focus_areas: List[str] = []
    early_vote_triggered: bool = False
```

### 6.2 新增数据库表

```sql
-- 评估历史
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motion_id TEXT NOT NULL,
    round INTEGER,
    result TEXT,
    consensus_level TEXT,
    metrics TEXT,  -- JSON
    rationale TEXT,
    created_at TEXT,
    FOREIGN KEY (motion_id) REFERENCES motions(id)
);
```

## 7. 优先级

| 功能 | 优先级 | 复杂度 | 说明 |
|------|--------|--------|------|
| 智能评估器 | P0 | 中 | 核心功能，判断讨论是否充分 |
| 提前投票 | P0 | 低 | 基于评估结果触发 |
| 分歧点聚焦 | P1 | 中 | 优化讨论效率 |
| 魔鬼代言人 | P1 | 中 | 防止一边倒讨论 |
| 话题重定向 | P2 | 高 | 需要 NLP 能力 |

## 8. 兼容性

所有 Phase 2 功能向后兼容 Phase 1：

- `smart_mode=False` 可禁用智能讨论，使用原固定轮次
- 投票系统不依赖智能讨论模块
- 魔鬼代言人可单独启用/禁用