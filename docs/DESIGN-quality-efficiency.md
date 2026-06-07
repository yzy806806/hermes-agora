# Phase 6: 讨论质量与效率增强

## 概述

Phase 6 目标：提升讨论质量和效率，让 Agora 的讨论不流于形式，真正产出高质量决策。

## 1. 讨论质量保证增强

### 1.1 当前问题

现有 `devils_advocate.py` 的检测逻辑过于简单：
- 只检查 `support_ratio >= 0.7` 就触发魔鬼代言人
- 缺乏对论据质量、证据充分性、观点多样性的评估
- 只有 devil_advocate 单一角色，无法应对复杂场景

### 1.2 增强方案

#### 1.2.1 质量检测维度

新增 `QualityGuard` 模块，检测以下场景：

```python
# coordinator/quality_guard.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional

class QualityIssue(str, Enum):
    """质量问题的类型"""
    LOW_ARGUMENT_QUALITY = "low_argument_quality"    # 论据质量低
    EVIDENCE_SPARSE = "evidence_sparse"              # 缺乏证据
    REPETITIVE_ARGUMENTS = "repetitive_arguments"    # 论据重复
    SINGLE_PERSPECTIVE = "single_perspective"        # 观点单一
    WEAK_REBUTTAL = "weak_rebuttal"                  # 反驳薄弱

@dataclass
class QualityAlert:
    """质量告警"""
    issue: QualityIssue
    severity: float  # 0.0-1.0
    details: str
    affected_agents: list[str]

class QualityGuard:
    """讨论质量守护者"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    async def check_quality(self, motion_id: str) -> list[QualityAlert]:
        """全面检查讨论质量"""
        messages = await self.storage.get_messages(motion_id)
        alerts = []
        
        # 1. 检查论据质量
        alerts.extend(await self._check_argument_quality(messages))
        
        # 2. 检查证据充分性
        alerts.extend(await self._check_evidence_sparsity(messages))
        
        # 3. 检查论据重复
        alerts.extend(await self._check_repetitive(messages))
        
        # 4. 检查观点多样性
        alerts.extend(await self._check_perspective_diversity(messages))
        
        return alerts
    
    async def _check_argument_quality(self, messages: list[dict]) -> list[QualityAlert]:
        """检查论据质量 - 检测短、无实质内容的发言"""
        alerts = []
        for msg in messages:
            content = msg.get("content", "")
            # 简单启发式：太短或无实质论点的发言
            if len(content) < 50 or self._is_trivial(content):
                alerts.append(QualityAlert(
                    issue=QualityIssue.LOW_ARGUMENT_QUALITY,
                    severity=0.7,
                    details=f"Agent {msg.get('agent_id')} 发言缺乏实质内容",
                    affected_agents=[msg.get("agent_id")],
                ))
        return alerts
    
    async def _check_evidence_sparsity(self, messages: list[dict]) -> list[QualityAlert]:
        """检查证据充分性"""
        no_evidence = [m for m in messages if len(m.get("evidence", [])) == 0]
        if len(no_evidence) / max(len(messages), 1) > 0.6:
            return [QualityAlert(
                issue=QualityIssue.EVIDENCE_SPARSE,
                severity=0.8,
                details=f"60%+ 发言缺乏证据支持",
                affected_agents=[m["agent_id"] for m in no_evidence],
            )]
        return []
    
    async def _check_repetitive(self, messages: list[dict]) -> list[QualityAlert]:
        """检测重复论据"""
        content_hashes = {}
        for msg in messages:
            h = hash(msg.get("content", "")[:100])  # 比较前100字符
            content_hashes[h] = content_hashes.get(h, 0) + 1
        
        duplicates = [h for h, c in content_hashes.items() if c > 1]
        if len(duplicates) > len(messages) * 0.3:
            return [QualityAlert(
                issue=QualityIssue.REPETITIVE_ARGUMENTS,
                severity=0.6,
                details="超过30%的发言内容重复",
                affected_agents=[],
            )]
        return []
    
    async def _check_perspective_diversity(self, messages: list[dict]) -> list[QualityAlert]:
        """检查观点多样性"""
        stances = [m.get("stance") for m in messages]
        unique = set(stances)
        if len(unique) < 2:
            return [QualityAlert(
                issue=QualityIssue.SINGLE_PERSPECTIVE,
                severity=0.9,
                details="讨论仅有一个立场",
                affected_agents=[],
            )]
        return []
    
    def _is_trivial(self, content: str) -> bool:
        """判断内容是否trivial"""
        trivial_phrases = ["同意", "支持", "反对", "没意见", "是的"]
        return any(content.strip() == p for p in trivial_phrases)
```

#### 1.2.2 多角色协作

扩展 AgentRole，支持更多讨论角色：

```python
# coordinator/models.py 扩展

class DiscussionRole(str, Enum):
    """讨论中的角色类型"""
    SUPPORTAdvocate = "support_advocate"     # 支持方
    OPPOSEAdvocate = "oppose_advocate"       # 反对方
    EXPERT = "expert"                         # 专家（提供专业知识）
    NEUTRAL = "neutral"                       # 中立（调解/总结）
    FACT_CHECKER = "fact_checker"             # 事实核查
    CREATIVE = "creative"                     # 创意（提出新观点）

@dataclass
class RoleAssignment:
    """角色分配"""
    agent_id: str
    role: DiscussionRole
    justification: str

class RoleDistributor:
    """根据质量告警分配角色"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    async def assign_roles(
        self, motion_id: str, alerts: list[QualityAlert]
    ) -> list[RoleAssignment]:
        """根据质量情况动态分配角色"""
        agents = await self.storage.list_agents()
        assignments = []
        
        # 根据告警类型选择角色
        has_quality_issue = any(
            a.issue == QualityIssue.LOW_ARGUMENT_QUALITY for a in alerts
        )
        if has_quality_issue:
            # 需要事实核查
            assignments.append(RoleAssignment(
                agent_id=self._select_agent(agents, "fact"),
                role=DiscussionRole.FACT_CHECKER,
                justification="论据质量不足，需要事实核查",
            ))
        
        has_single_perspective = any(
            a.issue == QualityIssue.SINGLE_PERSPECTIVE for a in alerts
        )
        if has_single_perspective:
            # 需要引入不同观点
            assignments.append(RoleAssignment(
                agent_id=self._select_agent(agents, "creative"),
                role=DiscussionRole.CREATIVE,
                justification="观点单一，需要新视角",
            ))
        
        return assignments
    
    def _select_agent(self, agents: list[dict], capability: str) -> str:
        """根据能力选择agent"""
        # 简化实现：随机选择
        return agents[0]["agent_id"] if agents else ""
```

### 1.3 讨论质量评分维度

新增多维度质量评分：

```python
@dataclass
class QualityScore:
    """质量评分"""
    evidence_sufficiency: float      # 证据充分性 0-1
    argument_logic: float            # 论据逻辑性 0-1
    perspective_diversity: float     # 观点多样性 0-1
    rebuttal_strength: float         # 反驳强度 0-1
    overall: float                   # 综合评分 0-1

class QualityScorer:
    """多维度质量评分器"""
    
    async def score(self, motion_id: str, storage: Storage) -> QualityScore:
        messages = await storage.get_messages(motion_id)
        
        evidence = self._score_evidence(messages)
        logic = self._score_logic(messages)
        diversity = self._score_diversity(messages)
        rebuttal = self._score_rebuttal(messages)
        
        return QualityScore(
            evidence_sufficiency=evidence,
            argument_logic=logic,
            perspective_diversity=diversity,
            rebuttal_strength=rebuttal,
            overall=(evidence * 0.3 + logic * 0.3 + 
                    diversity * 0.2 + rebuttal * 0.2),
        )
    
    def _score_evidence(self, messages: list[dict]) -> float:
        """证据充分性评分"""
        if not messages:
            return 0.0
        has_evidence = sum(1 for m in messages if m.get("evidence"))
        return min(has_evidence / len(messages), 1.0)
    
    def _score_logic(self, messages: list[dict]) -> float:
        """论据逻辑性 - 检查发言长度和结构"""
        if not messages:
            return 0.0
        avg_len = sum(len(m.get("content", "")) for m in messages) / len(messages)
        return min(avg_len / 200, 1.0)
    
    def _score_diversity(self, messages: list[dict]) -> float:
        """观点多样性"""
        stances = set(m.get("stance") for m in messages)
        return min(len(stances) / 3, 1.0)  # 3种立场为满分
    
    def _score_rebuttal(self, messages: list[dict]) -> float:
        """反驳强度 - 检测reply_to引用"""
        has_reply = sum(1 for m in messages if m.get("reply_to"))
        return min(has_reply / max(len(messages), 1), 1.0)
```

---

## 2. 效率优化 —— 动态轮次与共识点跳跃

### 2.1 当前问题

`smart_scheduler.py` 当前每轮结束后才评估：
- 无法实时检测共识点
- 固定 `max_rounds`，无法自适应
- 已达成共识的子议题仍被反复讨论

### 2.2 增强方案

#### 2.2.1 实时评估能力

```python
# coordinator/realtime_evaluator.py

from typing import Optional
from .assessment import ConsensusLevel

class RealTimeEvaluator:
    """实时评估器 - 在每条消息后检查"""
    
    def __init__(self, storage: Storage, consensus_threshold: float = 0.8):
        self.storage = storage
        self.consensus_threshold = consensus_threshold
    
    async def on_message(self, motion_id: str, message: dict) -> Optional[dict]:
        """每条消息后调用，返回评估结果"""
        messages = await self.storage.get_messages(motion_id)
        messages.append(message)  # 包含新消息
        
        # 快速检测共识
        consensus, level = self._detect_instant_consensus(messages)
        if consensus:
            return {
                "type": "INSTANT_CONSENSUS",
                "consensus_topic": consensus,
                "consensus_level": level,
                "action": "SKIP_NEXT_ROUNDS",  # 可跳过后续轮次
            }
        
        # 检测是否需要提前终止
        if self._should_end_early(messages):
            return {
                "type": "EARLY_TERMINATION",
                "reason": "quality_sufficient",
            }
        
        return None
    
    def _detect_instant_consensus(
        self, messages: list[dict]
    ) -> tuple[Optional[str], ConsensusLevel]:
        """检测即时共识 - 基于子议题分析"""
        # 简化：检查立场分布
        stances = [m.get("stance") for m in messages]
        total = len(stances)
        if total < 3:
            return None, ConsensusLevel.LOW
        
        support_count = stances.count("support")
        if support_count / total >= self.consensus_threshold:
            return "main_topic", ConsensusLevel.HIGH
        
        return None, ConsensusLevel.LOW
    
    def _should_end_early(self, messages: list[dict]) -> bool:
        """判断是否应该提前结束"""
        if len(messages) < 6:
            return False
        
        # 检查质量指标
        has_evidence = sum(1 for m in messages if m.get("evidence"))
        if has_evidence / len(messages) < 0.3:
            return False
        
        return True
```

#### 2.2.2 共识点跳跃机制

```python
# coordinator/consensus_jump.py

from dataclasses import dataclass, field

@dataclass
class SubTopicConsensus:
    """子议题共识状态"""
    topic: str
    consensus_reached: bool
    supporting_agents: list[str] = field(default_factory=list)
    opposing_agents: list[str] = field(default_factory=list)

class ConsensusJumpManager:
    """共识点跳跃管理器"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self._consensus_cache: dict[str, list[SubTopicConsensus]] = {}
    
    async def analyze_sub_topics(
        self, motion_id: str
    ) -> list[SubTopicConsensus]:
        """分析子议题的共识状态"""
        messages = await self.storage.get_messages(motion_id)
        
        # 简单实现：按stance分组
        by_stance = {"support": [], "oppose": [], "neutral": []}
        for msg in messages:
            s = msg.get("stance", "neutral")
            by_stance[s].append(msg.get("agent_id"))
        
        # 检测各立场的共识
        results = []
        for stance, agents in by_stance.items():
            if len(agents) >= 2:  # 2人以上同一立场
                results.append(SubTopicConsensus(
                    topic=f"stance_{stance}",
                    consensus_reached=True,
                    supporting_agents=agents,
                ))
        
        return results
    
    async def get_focus_topics(
        self, motion_id: str
    ) -> list[str]:
        """获取需要聚焦讨论的子议题"""
        sub_topics = await self.analyze_sub_topics(motion_id)
        # 只返回未达成共识的
        return [s.topic for s in sub_topics if not s.consensus_reached]
```

#### 2.2.3 动态轮次调整

```python
# coordinator/dynamic_rounds.py

@dataclass
class RoundConfig:
    """动态轮次配置"""
    min_rounds: int = 2        # 最小轮次
    max_rounds: int = 5        # 最大轮次
    adaptive: bool = True      # 是否自适应

class DynamicRoundManager:
    """动态轮次管理器"""
    
    def __init__(self, config: RoundConfig):
        self.config = config
    
    async def should_continue(
        self,
        motion_id: str,
        storage: Storage,
        quality_score: float,
        consensus_level: ConsensusLevel,
    ) -> tuple[bool, str]:
        """判断是否应该继续下一轮"""
        motion = await storage.get_motion(motion_id)
        current_round = motion.get("current_round", 0)
        
        # 1. 达到最小轮次前不考虑结束
        if current_round < self.config.min_rounds:
            return True, "min_rounds_not_met"
        
        # 2. 已达成高度共识，结束
        if consensus_level == ConsensusLevel.HIGH:
            return False, "consensus_reached"
        
        # 3. 质量足够且轮次合理，结束
        if (quality_score >= 0.7 and 
            current_round >= self.config.min_rounds):
            return False, "quality_sufficient"
        
        # 4. 达到最大轮次，强制结束
        if current_round >= self.config.max_rounds:
            return False, "max_rounds_reached"
        
        # 5. 自适应：质量停滞时延长
        if self.config.adaptive:
            if quality_score < 0.4:
                # 质量低，可能需要更多轮次
                return True, "quality_low_extend"
        
        return True, "continue"
```

---

## 3. 多模型差异利用

### 3.1 当前问题

不同模型有不同观点和知识偏好，但当前分配角色时未考虑这一点。

### 3.2 增强方案

#### 3.2.1 模型能力标签系统

```python
# coordinator/model_capabilities.py

from enum import Flag
from typing import Optional

class ModelCapability(Flag):
    """模型能力标志"""
    REASONING_STRONG = 1 << 0    # 推理能力强
    CREATIVE = 1 << 1            # 创意能力强
    FACTUAL = 1 << 2             # 事实核查强
    ANALYTICAL = 1 << 3          # 分析能力强
    DOMAIN_EXPERT = 1 << 4       # 领域专家

@dataclass
class ModelProfile:
    """模型画像"""
    model_name: str
    capabilities: ModelCapability
    preferred_stance: Optional[str] = None  # 天然倾向的立场
    weaknesses: list[str] = field(default_factory=list)

# 预设模型画像
MODEL_PROFILES: dict[str, ModelProfile] = {
    "gpt-4": ModelProfile(
        model_name="gpt-4",
        capabilities=ModelCapability.REASONING_STRONG | 
                     ModelCapability.ANALYTICAL,
        weaknesses=["可能过度谨慎"],
    ),
    "claude-3": ModelProfile(
        model_name="claude-3",
        capabilities=ModelCapability.CREATIVE | 
                     ModelCapability.FACTUAL,
        preferred_stance="neutral",
    ),
    "gemini": ModelProfile(
        model_name="gemini",
        capabilities=ModelCapability.REASONING_STRONG | 
                     ModelCapability.DOMAIN_EXPERT,
        weaknesses=["可能过于技术导向"],
    ),
}

class ModelProfiler:
    """模型能力分析器"""
    
    def get_profile(self, model_name: str) -> ModelProfile:
        """获取模型画像"""
        # 先查预设，没有则创建默认
        return MODEL_PROFILES.get(
            model_name.lower(),
            ModelProfile(
                model_name=model_name,
                capabilities=ModelCapability(0),
            )
        )
    
    def infer_capabilities(self, agent_id: str, storage: Storage) -> ModelProfile:
        """从agent历史发言推断能力"""
        # TODO: 可基于历史发言分析模型特点
        return self.get_profile("unknown")
```

#### 3.2.2 基于模型特点分配角色

```python
# coordinator/role_assigner.py

from .model_capabilities import ModelCapability, ModelProfiler
from .models import AgentInfo

class ModelAwareRoleAssigner:
    """模型感知角色分配器"""
    
    def __init__(self, storage: Storage, profiler: ModelProfiler):
        self.storage = storage
        self.profiler = profiler
    
    async def assign_optimal_roles(
        self, motion_id: str
    ) -> dict[str, DiscussionRole]:
        """为每个agent分配最优角色"""
        agents = await self.storage.list_agents()
        assignments = {}
        
        # 收集各能力类型的agent
        by_capability: dict[ModelCapability, list[dict]] = {
            ModelCapability.REASONING_STRONG: [],
            ModelCapability.CREATIVE: [],
            ModelCapability.FACTUAL: [],
            ModelCapability.ANALYTICAL: [],
        }
        
        for agent in agents:
            profile = self.profiler.get_profile(agent.get("model", ""))
            for cap in by_capability:
                if cap in profile.capabilities:
                    by_capability[cap].append(agent)
        
        # 分配角色
        # 1. 事实核查 -> FACTUAL 强
        if by_capability[ModelCapability.FACTUAL]:
            a = by_capability[ModelCapability.FACTUAL][0]
            assignments[a["agent_id"]] = DiscussionRole.FACT_CHECKER
        
        # 2. 创意观点 -> CREATIVE 强
        if by_capability[ModelCapability.CREATIVE]:
            a = by_capability[ModelCapability.CREATIVE][0]
            assignments[a["agent_id"]] = DiscussionRole.CREATIVE
        
        # 3. 专家观点 -> ANALYTICAL 强
        if by_capability[ModelCapability.ANALYTICAL]:
            a = by_capability[ModelCapability.ANALYTICAL][0]
            assignments[a["agent_id"]] = DiscussionRole.EXPERT
        
        # 剩余的作为普通参与者
        assigned = set(assignments.keys())
        for agent in agents:
            if agent["agent_id"] not in assigned:
                assignments[agent["agent_id"]] = DiscussionRole.NEUTRAL
        
        return assignments
    
    def get_role_instruction(self, role: DiscussionRole) -> str:
        """获取角色指令"""
        instructions = {
            DiscussionRole.FACT_CHECKER: 
                "请核查各方发言的事实准确性，指出任何不准确之处。",
            DiscussionRole.CREATIVE: 
                "请从非常规角度思考，提出创新性的观点和解决方案。",
            DiscussionRole.EXPERT: 
                "请运用专业知识，提供深度分析和技术见解。",
            DiscussionRole.NEUTRAL: 
                "请保持客观，总结各方观点，促进共识形成。",
        }
        return instructions.get(role, "请积极参与讨论。")
```

#### 3.2.3 确保观点多样性

```python
class PerspectiveEnsurer:
    """视角多样性保障器"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    async def ensure_diversity(
        self, motion_id: str, assignments: dict[str, DiscussionRole]
    ) -> list[str]:
        """确保讨论中有不同视角，返回需要补充的角色"""
        messages = await self.storage.get_messages(motion_id)
        
        # 检查现有立场分布
        stances = [m.get("stance") for m in messages]
        needed_roles = []
        
        if stances.count("support") == 0:
            needed_roles.append(DiscussionRole.SUPPORTAdvocate)
        if stances.count("oppose") == 0:
            needed_roles.append(DiscussionRole.OPPOSEAdvocate)
        if stances.count("neutral") < len(messages) * 0.2:
            needed_roles.append(DiscussionRole.NEUTRAL)
        
        return needed_roles
```

---

## 4. 集成方案

### 4.1 整体架构

```
SmartDiscussionScheduler (扩展)
├── QualityGuard          # 质量检测
├── QualityScorer         # 质量评分
├── RealTimeEvaluator     # 实时评估
├── ConsensusJumpManager  # 共识点跳跃
├── DynamicRoundManager   # 动态轮次
├── ModelAwareRoleAssigner # 模型感知角色分配
└── PerspectiveEnsurer    # 视角多样性保障
```

### 4.2 修改现有模块

1. **smart_scheduler.py** - 集成新模块
2. **assessment.py** - 扩展评估维度
3. **devils_advocate.py** - 增强检测逻辑
4. **models.py** - 新增 DiscussionRole 枚举

### 4.3 新增模块

| 模块 | 文件 | 职责 |
|------|------|------|
| QualityGuard | coordinator/quality_guard.py | 质量检测 |
| QualityScorer | coordinator/quality_scorer.py | 多维度评分 |
| RealTimeEvaluator | coordinator/realtime_evaluator.py | 实时评估 |
| ConsensusJumpManager | coordinator/consensus_jump.py | 共识跳跃 |
| DynamicRoundManager | coordinator/dynamic_rounds.py | 动态轮次 |
| ModelProfiler | coordinator/model_capabilities.py | 模型画像 |
| ModelAwareRoleAssigner | coordinator/role_assigner.py | 角色分配 |

---

## 5. 实现步骤

每个步骤不超过 80 行代码：

### 步骤 1: 质量守护者
- 创建 `quality_guard.py` - 基础质量检测
- 修改 `devils_advocate.py` 集成质量检测

### 步骤 2: 质量评分器
- 创建 `quality_scorer.py` - 多维度评分
- 修改 `assessment.py` 集成评分

### 步骤 3: 实时评估
- 创建 `realtime_evaluator.py` - 实时评估
- 修改 `smart_scheduler.py` 调用实时评估

### 步骤 4: 共识跳跃
- 创建 `consensus_jump.py` - 共识点分析
- 修改调度逻辑支持跳跃

### 步骤 5: 动态轮次
- 创建 `dynamic_rounds.py` - 动态轮次管理
- 修改 `smart_scheduler.py` 使用动态轮次

### 步骤 6: 模型能力标签
- 创建 `model_capabilities.py` - 模型画像
- 创建 `role_assigner.py` - 角色分配

### 步骤 7: 视角保障
- 创建 `perspective_ensurer.py` - 视角多样性
- 集成到角色分配流程

---

## 6. 向后兼容性

- 所有新增功能默认关闭，通过配置启用
- 保持现有 API 不变
- 新增的 WebSocket 消息类型使用新前缀避免冲突