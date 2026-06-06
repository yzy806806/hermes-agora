# Phase 2: Advanced Voting Design

## 概述

扩展投票系统，支持多种投票方法和非二元选择。保持与 Phase 1 简单多数投票的兼容性。

## 1. 投票方法体系

### 1.1 现有投票方法（Phase 1）

```python
# models.py - 已存在

class VotingMethod(str, Enum):
    SIMPLE_MAJORITY = "simple_majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"  # Phase 2 新增
    BORDA_COUNT = "borda_count"  # Phase 2 新增
    RANKED_CHOICE = "ranked_choice"  # Phase 2 新增
```

### 1.2 新增投票方法

```
投票方法分类：

1. 一选一投票（传统）
   - simple_majority   简单多数
   - supermajority    超多数（2/3）
   - unanimous        全票通过
   - weighted         加权投票

2. 多选一投票（非二元）
   - approval          认可投票（可多选）
   - range_vote       评分投票（0-10）
   - borda_count      波达计数法
   - instant_runoff   立即决选（排名）
```

## 2. 加权投票

### 2.1 设计原理

不同 Agent 根据其专业知识、经验或可信度有不同的投票权重。

```python
# coordinator/voting/weighted.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class WeightSource(str, Enum):
    """权重来源"""
    MANUAL = "manual"           # 手动设置
    REPUTATION = "reputation"   # 基于声誉
    EXPERTISE = "expertise"     # 基于专业领域
    STAKES = "stakes"           # 基于利益相关程度

@dataclass
class AgentWeight:
    """Agent 权重"""
    agent_id: str
    weight: float
    source: WeightSource
    reason: Optional[str] = None

@dataclass
class WeightedVoteResult:
    """加权投票结果"""
    decision: str
    total_weight_yes: float
    total_weight_no: float
    total_weight_abstain: float
    effective_yes: float
    effective_no: float
    threshold: float
    rationale: str

class WeightedVoting:
    """加权投票计算器"""
    
    def __init__(self, weights: Dict[str, float], threshold: float = 0.5):
        self.weights = weights
        self.threshold = threshold
    
    def count(self, votes: List[dict]) -> WeightedVoteResult:
        """统计加权投票结果"""
        total_weight_yes = 0.0
        total_weight_no = 0.0
        total_weight_abstain = 0.0
        
        for vote in votes:
            agent_id = vote["agent_id"]
            vote_choice = vote["vote"]
            weight = self.weights.get(agent_id, 1.0)  # 默认权重 1.0
            
            # 支持置信度加权
            confidence = vote.get("confidence", 1.0)
            effective_weight = weight * confidence
            
            if vote_choice == "yes":
                total_weight_yes += effective_weight
            elif vote_choice == "no":
                total_weight_no += effective_weight
            else:  # abstain
                total_weight_abstain += effective_weight
        
        total = total_weight_yes + total_weight_no
        
        if total == 0:
            return WeightedVoteResult(
                decision="no_consensus",
                total_weight_yes=total_weight_yes,
                total_weight_no=total_weight_no,
                total_weight_abstain=total_weight_abstain,
                effective_yes=0,
                effective_no=0,
                threshold=self.threshold,
                rationale="无有效投票"
            )
        
        # 计算有效权重比例
        effective_yes = total_weight_yes / (total_weight_yes + total_weight_no)
        
        if effective_yes >= self.threshold:
            decision = "adopted"
            rationale = f"加权多数通过：{total_weight_yes:.1f} 赞成 (有效比例 {effective_yes:.1%})"
        else:
            decision = "rejected"
            rationale = f"提案被否决：{total_weight_no:.1f} 反对"
        
        return WeightedVoteResult(
            decision=decision,
            total_weight_yes=total_weight_yes,
            total_weight_no=total_weight_no,
            total_weight_abstain=total_weight_abstain,
            effective_yes=effective_yes,
            effective_no=1 - effective_yes,
            threshold=self.threshold,
            rationale=rationale
        )
```

### 2.2 权重管理

```python
# coordinator/voting/weight_manager.py

class WeightManager:
    """权重管理器"""
    
    DEFAULT_WEIGHT = 1.0
    
    def __init__(self, storage: Storage, config: dict):
        self.storage = storage
        self.config = config
        self._weight_cache: Dict[str, Dict[str, float]] = {}  # motion_id -> {agent_id -> weight}
    
    async def get_weights(self, motion_id: str) -> Dict[str, float]:
        """获取议题的 Agent 权重"""
        if motion_id in self._weight_cache:
            return self._weight_cache[motion_id]
        
        # 从配置获取权重策略
        weights = {}
        
        if self.config.get("weight_strategy") == WeightSource.MANUAL:
            weights = self._get_manual_weights(motion_id)
        elif self.config.get("weight_strategy") == WeightSource.EXPERTISE:
            weights = await self._get_expertise_weights(motion_id)
        elif self.config.get("weight_strategy") == WeightSource.REPUTATION:
            weights = await self._get_reputation_weights()
        else:
            # 默认：等权重
            agents = await self.storage.list_agents()
            weights = {a.agent_id: self.DEFAULT_WEIGHT for a in agents}
        
        self._weight_cache[motion_id] = weights
        return weights
    
    async def _get_expertise_weights(self, motion_id: str) -> Dict[str, float]:
        """基于专业领域计算权重"""
        motion = await self.storage.get_motion(motion_id)
        
        # 从 motion 元数据获取相关领域
        relevant_domains = motion.context.get("relevant_domains", []) if motion.context else []
        
        agents = await self.storage.list_agents()
        weights = {}
        
        for agent in agents:
            # 检查 Agent 是否在相关领域有 expertise
            expertise = getattr(agent, "expertise", [])
            matching_domains = set(expertise) & set(relevant_domains)
            
            if matching_domains:
                # 有相关专业背景，权重加成
                weights[agent.agent_id] = 1.0 + 0.5 * len(matching_domains)
            else:
                weights[agent.agent_id] = self.DEFAULT_WEIGHT
        
        return weights
    
    async def _get_reputation_weights(self) -> Dict[str, float]:
        """基于声誉计算权重（历史投票准确率）"""
        # 简化版：基于历史参与次数
        agents = await self.storage.list_agents()
        
        # TODO: 实现真正的声誉系统
        return {a.agent_id: self.DEFAULT_WEIGHT for a in agents}
    
    def _get_manual_weights(self, motion_id: str) -> Dict[str, float]:
        """手动设置的权重"""
        return self.config.get("manual_weights", {})
```

## 3. 非二元选择

### 3.1 选项列表投票

支持 A/B/C 等多个选项：

```python
# coordinator/voting/multiple_choice.py

class MultipleChoiceVote:
    """多选项投票"""
    
    def __init__(self, options: List[str]):
        self.options = options
    
    def count(self, votes: List[dict]) -> dict:
        """统计多选项投票"""
        # 统计每个选项的得票
        option_counts = {opt: 0 for opt in self.options}
        abstain = 0
        
        for vote in votes:
            choice = vote.get("vote")
            if choice in option_counts:
                option_counts[choice] += 1
            elif choice == "abstain":
                abstain += 1
        
        total = sum(option_counts.values())
        
        if total == 0:
            return {
                "decision": "no_consensus",
                "results": option_counts,
                "abstain": abstain,
                "rationale": "无有效投票"
            }
        
        # 找出最高票
        winner = max(option_counts.items(), key=lambda x: x[1])
        
        # 判断是否通过（简单多数）
        if winner[1] > total / 2:
            decision = "adopted"
            rationale = f"选项 {winner[0]} 获得简单多数：{winner[1]}/{total}"
        else:
            decision = "no_consensus"
            rationale = f"最高票 {winner[0]} 未过半数：{winner[1]}/{total}"
        
        return {
            "decision": decision,
            "winner": winner[0] if decision == "adopted" else None,
            "results": option_counts,
            "abstain": abstain,
            "total": total,
            "rationale": rationale
        }
```

### 3.2 优先级排序投票（Ranked Choice）

```python
# coordinator/voting/ranked_choice.py

from collections import Counter

class RankedChoiceVoting:
    """优先级排序投票（Instant Runoff Voting）"""
    
    def count(self, ballots: List[dict]) -> dict:
        """
        IRV 算法：
        1. 统计第一选择
        2. 如果有候选人过半数，直接获胜
        3. 否则淘汰得票最少的，再次分配
        4. 重复直到产生获胜者
        """
        if not ballots:
            return {"decision": "no_consensus", "rationale": "无投票"}
        
        # 提取所有选项
        all_options = set()
        for ballot in ballots:
            ranking = ballot.get("ranking", [])
            all_options.update(ranking)
        
        if not all_options:
            return {"decision": "no_consensus", "rationale": "无效投票"}
        
        options = list(all_options)
        
        # 转换为排名字典
        ranked_ballots = []
        for ballot in ballots:
            ranking = ballot.get("ranking", [])
            if ranking:
                # 转为核心选字典：option -> rank
                ranked_ballots.append({opt: rank for rank, opt in enumerate(ranking)})
        
        # IRV 迭代
        return self._irv_iterate(ranked_ballots, options.copy())
    
    def _irv_iterate(self, ballots: List[dict], remaining_options: List[str]) -> dict:
        """IRV 迭代"""
        while remaining_options:
            # 统计第一选择
            first_choices = Counter()
            for ballot in ballots:
                # 找到第一个还在候选中的选项
                for opt in ballot:
                    if opt in remaining_options:
                        first_choices[opt] += 1
                        break
            
            total = sum(first_choices.values())
            
            if total == 0:
                return {"decision": "no_consensus", "rationale": "无有效选票"}
            
            # 检查是否有超过半数的
            for opt, count in first_choices.most_common():
                if count > total / 2:
                    return {
                        "decision": "adopted",
                        "winner": opt,
                        "results": dict(first_choices),
                        "rounds": 1,
                        "rationale": f"{opt} 获得过半数：{count}/{total}"
                    }
            
            # 淘汰得票最少的
            min_count = min(first_choices.values())
            eliminated = [opt for opt, count in first_choices.items() if count == min_count]
            
            if len(remaining_options) <= len(eliminated):
                # 无法继续淘汰，平局
                return {
                    "decision": "tie",
                    "leading": first_choices.most_common(3),
                    "rationale": f"平局：{eliminated}"
                }
            
            for opt in eliminated:
                remaining_options.remove(opt)
        
        return {"decision": "no_consensus", "rationale": "无法产生获胜者"}
```

### 3.3 评分投票（Range Voting）

```python
# coordinator/voting/range_voting.py

class RangeVoting:
    """评分投票（0-10 分）"""
    
    def __init__(self, min_score: int = 0, max_score: int = 10):
        self.min_score = min_score
        self.max_score = max_score
    
    def count(self, votes: List[dict]) -> dict:
        """统计评分投票"""
        if not votes:
            return {"decision": "no_consensus", "rationale": "无投票"}
        
        # 提取所有选项
        all_options = set()
        for vote in votes:
            scores = vote.get("scores", {})
            all_options.update(scores.keys())
        
        if not all_options:
            return {"decision": "no_consensus", "rationale": "无效投票"}
        
        # 计算每个选项的总分和平均分
        option_totals: Dict[str, List[float]] = {opt: [] for opt in all_options}
        
        for vote in votes:
            scores = vote.get("scores", {})
            for opt, score in scores.items():
                if self.min_score <= score <= self.max_score:
                    option_totals[opt].append(score)
        
        # 计算结果
        results = {}
        for opt, scores in option_totals.items():
            if scores:
                results[opt] = {
                    "total": sum(scores),
                    "average": sum(scores) / len(scores),
                    "count": len(scores),
                    "min": min(scores),
                    "max": max(scores)
                }
            else:
                results[opt] = {"total": 0, "average": 0, "count": 0}
        
        # 找出最高平均分
        winner = max(results.items(), key=lambda x: x[1]["average"])
        
        # 判断阈值（默认 5 分以上算通过）
        threshold = (self.max_score - self.min_score) / 2
        
        if winner[1]["average"] >= threshold:
            decision = "adopted"
            rationale = f"选项 {winner[0]} 最高平均分：{winner[1]['average']:.1f}"
        else:
            decision = "no_consensus"
            rationale = f"最高分 {winner[1]['average']:.1f} 未达阈值 {threshold}"
        
        return {
            "decision": decision,
            "winner": winner[0] if decision == "adopted" else None,
            "results": results,
            "threshold": threshold,
            "rationale": rationale
        }
```

### 3.4 认可投票（Approval Voting）

```python
# coordinator/voting/approval_voting.py

class ApprovalVoting:
    """认可投票（可多选）"""
    
    def count(self, votes: List[dict]) -> dict:
        """统计认可投票"""
        if not votes:
            return {"decision": "no_consensus", "rationale": "无投票"}
        
        # 收集所有选项
        all_options = set()
        for vote in votes:
            approved = vote.get("approved", [])
            all_options.update(approved)
        
        if not all_options:
            return {"decision": "no_consensus", "rationale": "无有效投票"}
        
        # 统计每个选项的认可票数
        option_counts = {opt: 0 for opt in all_options}
        
        for vote in votes:
            approved = vote.get("approved", [])
            for opt in approved:
                if opt in option_counts:
                    option_counts[opt] += 1
        
        total_voters = len(votes)
        
        # 找最高票
        winner = max(option_counts.items(), key=lambda x: x[1])
        
        # 简单多数判断
        if winner[1] > total_voters / 2:
            decision = "adopted"
            rationale = f"{winner[0]} 获得认可票最多：{winner[1]}/{total_voters}"
        else:
            decision = "no_consensus"
            rationale = f"最高票 {winner[0]} 未过半数"
        
        return {
            "decision": decision,
            "winner": winner[0] if decision == "adopted" else None,
            "results": option_counts,
            "total_voters": total_voters,
            "rationale": rationale
        }
```

## 4. 统一投票接口

### 4.1 投票工厂

```python
# coordinator/voting/factory.py

from typing import Dict

class VoteCounterFactory:
    """投票计数器工厂"""
    
    _counters: Dict[VotingMethod, Any] = {}
    
    @classmethod
    def register(cls, method: VotingMethod, counter):
        cls._counters[method] = counter
    
    @classmethod
    def get_counter(cls, method: VotingMethod):
        if method not in cls._counters:
            # 默认使用简单多数
            return SimpleMajorityCounter()
        return cls._counters[method]

# 注册所有投票方法
VoteCounterFactory.register(VotingMethod.SIMPLE_MAJORITY, SimpleMajorityCounter())
VoteCounterFactory.register(VotingMethod.SUPERMAJORITY, SupermajorityCounter())
VoteCounterFactory.register(VotingMethod.UNANIMOUS, UnanimousCounter())
VoteCounterFactory.register(VotingMethod.WEIGHTED, WeightedVoting(weights={}, threshold=0.5))
VoteCounterFactory.register(VotingMethod.BORDA_COUNT, BordaCountVoting())
VoteCounterFactory.register(VotingMethod.RANKED_CHOICE, RankedChoiceVoting())
```

### 4.2 统一投票管理器

```python
# coordinator/voting/manager.py

class AdvancedVotingManager:
    """高级投票管理器"""
    
    def __init__(self, storage: Storage, ws_manager: ConnectionManager, config: Settings):
        self.storage = storage
        self.ws_manager = ws_manager
        self.weight_manager = WeightManager(storage, config)
        self.factory = VoteCounterFactory()
    
    async def handle_vote(self, agent_id: str, motion_id: str, 
                          vote_data: dict) -> None:
        """处理投票"""
        motion = await self.storage.get_motion(motion_id)
        
        if motion.status != MotionStatus.VOTING:
            await self.ws_manager.send(agent_id, {
                "type": "ERROR",
                "payload": {"code": "INVALID_STATE", "message": "不在投票阶段"}
            })
            return
        
        # 检查是否支持该投票方法
        if not self._supports_voting_method(motion.voting_method, vote_data):
            await self.ws_manager.send(agent_id, {
                "type": "ERROR",
                "payload": {"code": "INVALID_VOTE_FORMAT", "message": "投票格式不匹配"}
            })
            return
        
        # 存储投票
        await self.storage.add_vote(
            motion_id=motion_id,
            agent_id=agent_id,
            vote=vote_data.get("vote"),
            vote_data=json.dumps(vote_data),
            confidence=vote_data.get("confidence", 1.0),
            reason=vote_data.get("reason")
        )
        
        # 确认投票
        await self.ws_manager.send(agent_id, {
            "type": "VOTE_CONFIRMED",
            "motion_id": motion_id,
            "payload": {"vote": vote_data.get("vote")}
        })
        
        # 检查是否全部投票
        await self._check_all_voted(motion_id)
    
    def _supports_voting_method(self, method: VotingMethod, vote_data: dict) -> bool:
        """检查投票格式是否匹配"""
        vote_type = vote_data.get("type", "binary")
        
        if method in [VotingMethod.SIMPLE_MAJORITY, VotingMethod.SUPERMAJORITY, VotingMethod.UNANIMOUS]:
            return vote_type == "binary" and "vote" in vote_data
        elif method == VotingMethod.WEIGHTED:
            return vote_type == "binary" and "vote" in vote_data
        elif method == VotingMethod.RANKED_CHOICE:
            return vote_type == "ranking" and "ranking" in vote_data
        elif method == ApprovalVoting:
            return vote_type == "approval" and "approved" in vote_data
        else:
            return True
    
    async def close_voting(self, motion_id: str) -> None:
        """关闭投票并计算结果"""
        motion = await self.storage.get_motion(motion_id)
        votes = await self.storage.get_votes(motion_id)
        
        # 获取计数器
        if motion.voting_method == VotingMethod.WEIGHTED:
            weights = await self.weight_manager.get_weights(motion_id)
            counter = WeightedVoting(weights=weights, threshold=0.5)
        else:
            counter = VoteCounterFactory.get_counter(motion.voting_method)
        
        # 计算结果
        result = counter.count(votes)
        
        # 更新状态
        await self.storage.update_motion_status(motion_id, MotionStatus.CLOSED)
        
        # 保存结果
        await self.storage.save_result(motion_id, result)
        
        # 广播结果
        await self.ws_manager.broadcast({
            "type": "RESULT",
            "motion_id": motion_id,
            "payload": {
                "decision": result.get("decision"),
                "voting_method": motion.voting_method,
                "results": result,
                "rationale": result.get("rationale")
            }
        })
```

## 5. 数据模型扩展

### 5.1 Vote 表扩展

```sql
-- 扩展 votes 表支持多种投票格式

ALTER TABLE votes ADD COLUMN vote_type TEXT DEFAULT 'binary';
ALTER TABLE votes ADD COLUMN vote_data TEXT;  -- JSON 存储完整投票数据
```

### 5.2 Motion 扩展

```python
# models.py 扩展

class MotionCreateRequest(BaseModel):
    # ... 现有 ...
    
    # Phase 2 新增
    voting_options: Optional[List[str]] = None  # 多选项时使用
    voting_config: Optional[Dict] = None  # 投票配置（权重、加权系数等）
```

### 5.3 请求格式定义

```python
# 各种投票请求格式

class BinaryVoteRequest(BaseModel):
    """二元投票"""
    vote: VoteChoice  # yes/no/abstain
    confidence: float = 1.0
    reason: Optional[str] = None

class MultipleChoiceVoteRequest(BaseModel):
    """多选项投票"""
    type: str = "multiple_choice"
    vote: str  # 选项名
    confidence: float = 1.0
    reason: Optional[str] = None

class RankingVoteRequest(BaseModel):
    """排序投票"""
    type: str = "ranking"
    ranking: List[str]  # 按优先级排序的选项列表
    confidence: float = 1.0

class ApprovalVoteRequest(BaseModel):
    """认可投票"""
    type: str = "approval"
    approved: List[str]  # 认可的选项列表
    confidence: float = 1.0

class RangeVoteRequest(BaseModel):
    """评分投票"""
    type: str = "range"
    scores: Dict[str, float]  # {option: score}
    confidence: float = 1.0
```

## 6. WebSocket 消息扩展

### 6.1 投票请求

```python
# 投票阶段发送的 REQUEST_VOTE 扩展

{
    "type": "REQUEST_VOTE",
    "motion_id": "xxx",
    "payload": {
        "voting_method": "ranked_choice",
        "options": ["A方案", "B方案", "C方案"],
        "description": "请按优先级排序（1最高）",
        "min_ranking": 1,
        "max_ranking": 3
    }
}
```

### 6.2 投票响应

```python
# 客户端投票

{
    "type": "VOTE",
    "motion_id": "xxx",
    "payload": {
        "type": "ranking",
        "ranking": ["B方案", "A方案", "C方案"],
        "confidence": 0.8
    }
}
```

## 7. 接口变更

### 7.1 创建议题时指定投票方法

```python
@router.post("/motions", response_model=Motion)
async def create_motion(request: MotionCreateRequest):
    """创建议题"""
    # 验证投票方法是否支持
    if request.voting_method == VotingMethod.WEIGHTED:
        if not request.voting_config or "weights" not in request.voting_config:
            raise HTTPException(400, "加权投票需要配置权重")
    
    # ... 其余逻辑
```

### 7.2 获取投票结果

```python
@router.get("/motions/{motion_id}/result")
async def get_result(motion_id: str):
    """讨论结果"""
    motion = await storage.get_motion(motion_id)
    votes = await storage.get_votes(motion_id)
    
    # 根据投票方法返回对应结果格式
    if motion.voting_method == VotingMethod.RANKED_CHOICE:
        # 返回 IRV 详细信息
        return {...}
```

## 8. 优先级

| 功能 | 优先级 | 复杂度 | 说明 |
|------|--------|--------|------|
| 加权投票 | P0 | 中 | 核心功能，Phase 2 重点 |
| 多选项投票 | P0 | 低 | 扩展简单多数 |
| 排序投票（IRV） | P1 | 高 | 复杂但更公平 |
| 评分投票 | P2 | 中 | 需要用户理解 |
| 认可投票 | P2 | 低 | 简单实用 |

## 9. 向后兼容

- 现有 simple_majority / supermajority / unanimous 行为不变
- 旧版投票客户端只发送 binary 格式，新版自动识别
- 不指定 voting_options 时默认为 ["yes", "no", "abstain"]