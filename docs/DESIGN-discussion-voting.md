# Phase 1: 单轮讨论 + 简单多数投票设计

## 概述

设计最简单的讨论流程：发起议题 → Agent 轮流发言 → 投票 → 出结果。实现简单多数制投票。

## 1. 讨论流程设计

### 1.1 流程状态机

```
[DRAFT] → [DISCUSSING] → [VOTING] → [CLOSED]
              ↓              ↓
           (轮次进行)    (等待投票)
```

### 1.2 完整流程步骤

```
1. 用户创建议题 (POST /motions)
   └── State: DRAFT

2. 用户开始讨论 (POST /motions/{id}/start)
   └── State: DISCUSSING
   └── 广播 NEW_MOTION 给所有在线 Agent

3. 轮次发言 (每轮每个 Agent 发言一次)
   FOR round = 1 to N:
     FOR each agent in registered_agents:
       - 发送 SPEAK 请求给该 Agent
       - Agent 提交发言内容
       - 广播 BROADCAST 给所有 Agent
       - 存储发言到数据库

4. 轮次完成检查
   - 如果还有轮次 → 继续下一轮
   - 如果轮次完成 → 进入投票阶段
   └── State: VOTING
   └── 广播 REQUEST_VOTE 给所有 Agent

5. Agent 投票
   FOR each agent:
     - Agent 提交投票
     - 存储投票到数据库
     
6. 投票完成检查
   - 如果所有 Agent 已投票 → 关闭议题
   └── State: CLOSED
   └── 计算结果
   └── 广播 RESULT 给所有 Agent
```

### 1.3 发言轮次调度

```python
# coordinator/discuss.py

class DiscussionScheduler:
    """发言轮次调度器"""
    
    def __init__(self, storage: Storage, ws_manager: ConnectionManager):
        self.storage = storage
        self.ws_manager = ws_manager
    
    async def start_discussion(self, motion_id: str) -> None:
        """开始讨论，广播议题给所有 Agent"""
        motion = await self.storage.get_motion(motion_id)
        agents = await self.storage.list_agents()
        
        if not agents:
            raise ValueError("No agents registered")
        
        await self.storage.update_motion_status(motion_id, MotionStatus.DISCUSSING)
        await self.storage.update_motion_round(motion_id, 1)
        
        # 广播新议题给所有 Agent
        await self.ws_manager.broadcast({
            "type": "NEW_MOTION",
            "motion_id": motion_id,
            "payload": {
                "title": motion.title,
                "description": motion.description,
                "context": motion.context,
                "rounds": motion.rounds,
                "voting_method": motion.voting_method,
                "current_round": 1,
            }
        })
        
        # 触发第一轮发言
        await self.request_next_speak(motion_id)
    
    async def request_next_speak(self, motion_id: str) -> None:
        """请求下一个发言"""
        motion = await self.storage.get_motion(motion_id)
        agents = await self.storage.list_agents()
        
        # 找出当前轮次未发言的 Agent
        current_round = motion.current_round
        spoken_agents = await self.storage.get_speakers_in_round(motion_id, current_round)
        
        remaining = [a for a in agents if a.agent_id not in spoken_agents]
        
        if remaining:
            # 还有 Agent 未发言，请求下一个
            next_agent = remaining[0]
            await self.ws_manager.send(next_agent.agent_id, {
                "type": "REQUEST_SPEAK",
                "motion_id": motion_id,
                "payload": {
                    "round": current_round,
                    "topic": motion.title,
                    "description": motion.description,
                }
            })
        else:
            # 本轮结束，检查是否还有轮次
            if current_round >= motion.rounds:
                # 所有轮次完成，进入投票
                await self.transition_to_voting(motion_id)
            else:
                # 进入下一轮
                await self.storage.update_motion_round(motion_id, current_round + 1)
                new_round = current_round + 1
                
                await self.ws_manager.broadcast({
                    "type": "ROUND_COMPLETE",
                    "motion_id": motion_id,
                    "payload": {"round": current_round}
                })
                
                # 请求下一轮第一个发言
                await self.request_next_speak(motion_id)
    
    async def handle_speak(self, agent_id: str, motion_id: str, content: str, stance: str) -> None:
        """处理发言"""
        motion = await self.storage.get_motion(motion_id)
        
        # 存储发言
        await self.storage.add_message(
            motion_id=motion_id,
            agent_id=agent_id,
            round=motion.current_round,
            stance=stance,
            content=content,
            evidence=[]
        )
        
        # 广播发言给所有 Agent
        agent = await self.storage.get_agent(agent_id)
        await self.ws_manager.broadcast({
            "type": "BROADCAST",
            "motion_id": motion_id,
            "payload": {
                "speaker_id": agent_id,
                "speaker_name": agent.name if agent else agent_id,
                "round": motion.current_round,
                "stance": stance,
                "content": content
            }
        })
        
        # 请求下一个发言
        await self.request_next_speak(motion_id)
    
    async def transition_to_voting(self, motion_id: str) -> None:
        """transition 到投票阶段"""
        await self.storage.update_motion_status(motion_id, MotionStatus.VOTING)
        motion = await self.storage.get_motion(motion_id)
        
        # 生成讨论摘要 (Phase 2 智能摘要)
        summary = await self.generate_summary(motion_id)
        
        await self.ws_manager.broadcast({
            "type": "REQUEST_VOTE",
            "motion_id": motion_id,
            "payload": {
                "summary": summary,
                "options": ["yes", "no", "abstain"]
            }
        })
    
    async def generate_summary(self, motion_id: str) -> str:
        """生成讨论摘要 (简化版)"""
        messages = await self.storage.get_messages(motion_id)
        
        if not messages:
            return "无讨论内容"
        
        support_count = sum(1 for m in messages if m.get("stance") == "support")
        oppose_count = sum(1 for m in messages if m.get("stance") == "oppose")
        neutral_count = sum(1 for m in messages if m.get("stance") == "neutral")
        
        return f"讨论完成：支持 {support_count}，反对 {oppose_count}，中立 {neutral_count}。请投票。"
```

## 2. 投票系统设计

### 2.1 简单多数制 (Simple Majority)

```
规则：赞成票 > 反对票 则通过
      否则 拒绝或无共识
```

```python
# coordinator/voting.py

from enum import Enum
from typing import Dict, List
from .models import VoteChoice, VotingMethod

class VoteCounter:
    """投票计数器"""
    
    def count(self, votes: List[dict], method: VotingMethod) -> Dict:
        """统计投票结果"""
        
        if method == VotingMethod.SIMPLE_MAJORITY:
            return self._simple_majority(votes)
        elif method == VotingMethod.SUPERMAJORITY:
            return self._supermajority(votes)
        elif method == VotingMethod.UNANIMOUS:
            return self._unanimous(votes)
        else:
            return self._simple_majority(votes)
    
    def _simple_majority(self, votes: List[dict]) -> Dict:
        """简单多数制"""
        yes = sum(1 for v in votes if v["vote"] == "yes")
        no = sum(1 for v in votes if v["vote"] == "no")
        abstain = sum(1 for v in votes if v["vote"] == "abstain")
        
        total = yes + no  # 、有效票（不含弃权）
        
        if total == 0:
            return {
                "decision": "no_consensus",
                "votes": {"yes": yes, "no": no, "abstain": abstain},
                "rationale": "无有效投票"
            }
        
        if yes > no:
            decision = "adopted"
            rationale = f"简单多数通过：{yes} 赞成 vs {no} 反对"
        elif no > yes:
            decision = "rejected"
            rationale = f"提案被否决：{no} 反对 vs {yes} 赞成"
        else:
            decision = "no_consensus"
            rationale = f"平票，无法达成共识：{yes} 赞成 vs {no} 反对"
        
        return {
            "decision": decision,
            "votes": {"yes": yes, "no": no, "abstain": abstain},
            "rationale": rationale
        }
    
    def _supermajority(self, votes: List[dict]) -> Dict:
        """2/3 多数制"""
        yes = sum(1 for v in votes if v["vote"] == "yes")
        no = sum(1 for v in votes if v["vote"] == "no")
        abstain = sum(1 for v in votes if v["vote"] == "abstain")
        
        total = yes + no
        
        if total == 0:
            return {
                "decision": "no_consensus",
                "votes": {"yes": yes, "no": no, "abstain": abstain},
                "rationale": "无有效投票"
            }
        
        # 需要 2/3 多数
        threshold = total * 2 / 3
        
        if yes >= threshold:
            decision = "adopted"
            rationale = f"超多数通过：{yes}/{total} 赞成 (≥{threshold:.1f})"
        elif no > total - threshold:
            decision = "rejected"
            rationale = f"超多数反对：{no}/{total} 反对"
        else:
            decision = "no_consensus"
            rationale = f"未达到超多数：{yes}/{total} 赞成"
        
        return {
            "decision": decision,
            "votes": {"yes": yes, "no": no, "abstain": abstain},
            "rationale": rationale
        }
    
    def _unanimous(self, votes: List[dict]) -> Dict:
        """全票通过制"""
        yes = sum(1 for v in votes if v["vote"] == "yes")
        no = sum(1 for v in votes if v["vote"] == "no")
        abstain = sum(1 for v in votes if v["vote"] == "abstain")
        
        total = yes + no
        
        if total == 0:
            return {
                "decision": "no_consensus",
                "votes": {"yes": yes, "no": no, "abstain": abstain},
                "rationale": "无有效投票"
            }
        
        if no == 0 and yes > 0:
            decision = "adopted"
            rationale = f"全票通过：{yes} 赞成"
        else:
            decision = "rejected"
            rationale = f"未达成全票通过：{yes} 赞成，{no} 反对"
        
        return {
            "decision": decision,
            "votes": {"yes": yes, "no": no, "abstain": abstain},
            "rationale": rationale
        }
```

### 2.2 投票处理流程

```python
# coordinator/voting.py (continued)

class VotingManager:
    """投票管理器"""
    
    def __init__(self, storage: Storage, ws_manager: ConnectionManager):
        self.storage = storage
        self.ws_manager = ws_manager
        self.counter = VoteCounter()
    
    async def handle_vote(self, agent_id: str, motion_id: str, 
                          vote: str, confidence: float, reason: str) -> None:
        """处理投票"""
        # 检查是否可以投票
        motion = await self.storage.get_motion(motion_id)
        if motion.status != MotionStatus.VOTING:
            await self.ws_manager.send(agent_id, {
                "type": "ERROR",
                "payload": {"code": "INVALID_STATE", "message": "Motion not in voting phase"}
            })
            return
        
        # 检查是否已投票
        if await self.storage.has_voted(motion_id, agent_id):
            await self.ws_manager.send(agent_id, {
                "type": "ERROR",
                "payload": {"code": "ALREADY_VOTED", "message": "Already voted"}
            })
            return
        
        # 存储投票
        await self.storage.add_vote(
            motion_id=motion_id,
            agent_id=agent_id,
            vote=vote,
            confidence=confidence,
            reason=reason
        )
        
        # 确认投票
        await self.ws_manager.send(agent_id, {
            "type": "VOTE_CONFIRMED",
            "motion_id": motion_id,
            "payload": {"vote": vote}
        })
        
        # 检查是否所有 Agent 都已投票
        await self.check_all_voted(motion_id)
    
    async def check_all_voted(self, motion_id: str) -> None:
        """检查是否所有 Agent 都已投票"""
        agents = await self.storage.list_agents()
        votes = await self.storage.get_votes(motion_id)
        
        voted_agents = set(v["agent_id"] for v in votes)
        all_agents = set(a.agent_id for a in agents)
        
        if voted_agents == all_agents:
            # 所有 Agent 都已投票，计算结果
            await self.close_voting(motion_id)
    
    async def close_voting(self, motion_id: str) -> None:
        """关闭投票，计算结果"""
        motion = await self.storage.get_motion(motion_id)
        votes = await self.storage.get_votes(motion_id)
        
        # 统计结果
        result = self.counter.count(votes, motion.voting_method)
        
        # 更新状态
        await self.storage.update_motion_status(motion_id, MotionStatus.CLOSED)
        
        # 生成行动项 (简化版)
        action_items = self._generate_action_items(result["decision"])
        
        # 广播结果
        await self.ws_manager.broadcast({
            "type": "RESULT",
            "motion_id": motion_id,
            "payload": {
                "decision": result["decision"],
                "votes": result["votes"],
                "rationale": result["rationale"],
                "action_items": action_items
            }
        })
        
        # 存储结果
        await self.storage.save_result(motion_id, result)
    
    def _generate_action_items(self, decision: str) -> List[str]:
        """生成行动项"""
        if decision == "adopted":
            return ["执行提案", "跟踪执行效果"]
        elif decision == "rejected":
            return ["重新评估提案", "寻找替代方案"]
        else:
            return ["继续讨论", "寻求更多共识"]
```

## 3. 数据模型扩展

### 3.1 发言表扩展

```python
# 在 storage.py 中添加

async def get_speakers_in_round(self, motion_id: str, round: int) -> set[str]:
    """获取指定轮次已发言的 Agent ID 集合"""
    async with aiosqlite.connect(self.db_path) as db:
        async with db.execute(
            "SELECT DISTINCT agent_id FROM messages WHERE motion_id = ? AND round = ?",
            (motion_id, round)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0] for row in rows}

async def update_motion_round(self, motion_id: str, round: int) -> None:
    """更新当前轮次"""
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            "UPDATE motions SET current_round = ?, updated_at = ? WHERE id = ?",
            (round, datetime.utcnow().isoformat(), motion_id)
        )
        await db.commit()

async def save_result(self, motion_id: str, result: dict) -> None:
    """保存讨论结果"""
    import json
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            "UPDATE motions SET result = ?, updated_at = ? WHERE id = ?",
            (json.dumps(result), datetime.utcnow().isoformat(), motion_id)
        )
        await db.commit()
```

### 3.2 新增 WebSocket 消息类型

```python
# models.py 新增

class MessageType(str, Enum):
    # ... 现有类型 ...
    REQUEST_SPEAK = "REQUEST_SPEAK"    # 请求发言
    ROUND_COMPLETE = "ROUND_COMPLETE"  # 轮次完成
    VOTE_CONFIRMED = "VOTE_CONFIRMED"  # 投票确认
```

## 4. 接口变更

### 4.1 新增 HTTP 端点

```python
# router.py 新增

@router.post("/motions/{motion_id}/start")
async def start_motion(motion_id: str):
    """开始讨论"""
    scheduler = DiscussionScheduler(storage, manager)
    await scheduler.start_discussion(motion_id)
    return {"status": "started"}

@router.post("/motions/{motion_id}/close")
async def close_motion(motion_id: str):
    """手动关闭议题（提前结束）"""
    await state_machine.transition(motion_id, "all_voted")
    voting_manager = VotingManager(storage, manager)
    await voting_manager.close_voting(motion_id)
    return {"status": "closed"}
```

## 5. 异常处理

| 错误码 | 场景 | 处理 |
|--------|------|------|
| `NO_AGENTS` | 开始讨论时无 Agent | 返回 400 错误 |
| `ALREADY_DISCUSSING` | 重复开始讨论 | 返回 409 错误 |
| `ROUND_IN_PROGRESS` | 轮次未完成 | 提示等待 |
| `ALL_AGENTS_VOTED` | 所有 Agent 已投票 | 自动计算结果 |

## 6. 简化设计决策

1. **轮次固定**：所有 Agent 轮流发言 N 轮（N 可配置，默认 3）
2. **发言顺序**：按 Agent 注册顺序，或随机顺序
3. **投票强制**：所有在线 Agent 必须投票，缺席视为弃权
4. **无权重**：简单多数制不考虑 Agent 可信度差异
5. **无超时处理**：Phase 1 假设 Agent 响应正常

## 7. 后续扩展 (Phase 2)

- 智能判断讨论是否充分（不固定轮次）
- 魔鬼代言人机制
- 多种投票方式选择
- 分歧点聚焦
- 动态轮次调整