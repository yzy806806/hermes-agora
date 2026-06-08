# Hermes Agora 架构文档

> 版本: v0.7.0 | 最后更新: 2026-06

## 整体架构

```
                    ┌─────────────────────────────────┐
                    │       Coordinator Agent          │
                    │  (FastAPI + WebSocket 服务)       │
                    │  ┌──────────┐ ┌───────────────┐  │
                    │  │ REST API │ │ WebSocket Hub  │  │
                    │  └────┬─────┘ └──────┬────────┘  │
                    │       │    ┌─────────┤           │
                    │  ┌────▼────▼─┐ ┌─────▼────────┐  │
                    │  │ State     │ │ Smart Discuss │  │
                    │  │ Machine   │ │ Engine        │  │
                    │  └───────────┘ └──────────────┘  │
                    │  ┌───────────┐ ┌───────────────┐  │
                    │  │ Voting    │ │ Bootstrap     │  │
                    │  │ System    │ │ Engine        │  │
                    │  └───────────┘ └───────────────┘  │
                    │  ┌───────────┐ ┌───────────────┐  │
                    │  │ Fault     │ │ Quality       │  │
                    │  │ Tolerance │ │ Guard         │  │
                    │  └───────────┘ └───────────────┘  │
                    │  ┌───────────────────────────┐    │
                    │  │ Storage (SQLite)          │    │
                    │  └───────────────────────────┘    │
                    └────────────┬────────────────────┘
                                 │ WebSocket
        ┌────────────────────────┼────────────────────────┐
        ↓                        ↓                        ↓
   ┌─────────┐            ┌─────────┐            ┌─────────┐
   │ Hermes A│            │ Hermes B│            │ Hermes C│
   │ + Agora │            │ + Agora │            │ + Agora │
   │  Client │            │  Client │            │  Client │
   └─────────┘            └─────────┘            └─────────┘
```

## 项目目录结构

```
hermes-agora/
├── __init__.py              # Hermes 插件入口 + register()
├── plugin.yaml              # 插件元数据
├── commands.py              # /agora 斜杠命令路由
├── cmd_new.py               # /agora new 子命令
├── cmd_list.py              # /agora list 子命令
├── cmd_status.py            # /agora status 子命令
├── cmd_vote.py              # /agora vote 子命令
├── cmd_result.py            # /agora result 子命令
├── coordinator/             # 调度中心（FastAPI 服务）
│   ├── main.py              # 入口 + 生命周期管理
│   ├── config.py            # 配置（pydantic-settings）
│   ├── models.py            # 数据模型 + 枚举
│   ├── state.py             # 讨论状态机
│   ├── router.py            # REST API 路由
│   ├── ws.py                # WebSocket 连接管理器
│   ├── ws_endpoint.py       # WebSocket 端点 + 消息路由
│   ├── ws_handlers.py       # PING/REGISTER/SPEAK 处理
│   ├── ws_smart.py          # 智能讨论评估
│   ├── ws_vote.py           # VOTE 处理 + 投票完成检测
│   ├── assessment.py        # 讨论评估引擎
│   ├── consensus_jump.py    # 共识提前判断
│   ├── devils_advocate.py   # 魔鬼代言人
│   ├── focus.py             # 分歧点聚焦
│   ├── dynamic_rounds.py    # 动态轮次调整
│   ├── smart_scheduler.py   # 智能调度
│   ├── realtime_evaluator.py# 实时评估
│   ├── quality_scorer.py    # 质量评分
│   ├── quality_guard.py     # 质量守卫
│   ├── quality_guard_checks.py # 质量检查函数
│   ├── quality_guard_models.py # 质量守卫数据模型
│   ├── perspective_ensurer.py  # 视角保障
│   ├── role_assigner.py     # 讨论角色分配
│   ├── model_capabilities.py   # 模型能力识别
│   ├── curator.py           # 策略优化（进化闭环）
│   ├── memory_sync.py       # 讨论经验同步
│   ├── history_pattern.py   # 历史模式分析
│   ├── similar_topic.py     # 相似议题检索
│   ├── judgment_tracker.py  # 判断追踪
│   ├── judgment_types.py    # 判断类型定义
│   ├── conclusion_types.py  # 结论类型定义
│   ├── heartbeat.py         # 心跳监控
│   ├── timeout.py           # 超时管理
│   ├── deadlock_prevention.py # 死锁预防
│   ├── input_validation.py  # 输入验证 + 清洗
│   ├── rate_limiter.py      # 速率限制
│   ├── voting/              # 投票子系统
│   │   ├── __init__.py
│   │   ├── factory.py       # 投票策略工厂
│   │   ├── manager.py       # 投票管理器
│   │   ├── weighted.py      # 加权投票
│   │   ├── weighted_types.py# 加权类型定义
│   │   ├── weight_manager.py# 权重管理
│   │   ├── ranked_choice.py # 排序选择投票
│   │   ├── approval_voting.py # 批准投票
│   │   ├── range_voting.py  # 评分投票
│   │   └── multiple_choice.py # 多选投票
│   ├── bootstrap/           # 自举系统
│   │   ├── __init__.py      # BootstrapEngine
│   │   ├── trigger_types.py # 触发器类型
│   │   ├── trigger_manager.py # 触发器管理
│   │   ├── schedule_checker.py # 定时检查
│   │   ├── task_generator.py # 议题生成
│   │   ├── discussion_driver.py # 讨论驱动
│   │   ├── approval_flow.py # 审批流程
│   │   ├── bootstrap_schema.py # 自举数据模型
│   │   ├── routes.py        # Bootstrap REST 路由
│   │   └── routes_extra.py  # 审批/调度路由
│   └── storage/             # 数据存储层
│       ├── __init__.py      # Storage 入口
│       ├── schema.py        # 数据库 Schema
│       ├── storage.py       # 核心存储操作
│       ├── agents.py        # Agent 存储
│       ├── motions.py       # 议题存储
│       ├── messages.py      # 消息存储
│       ├── votes.py         # 投票存储
│       ├── assessments.py   # 评估存储
│       ├── judgments.py     # 判断存储
│       ├── bootstrap.py     # 自举存储
│       └── bootstrap_approval.py # 审批存储
├── agent_client/            # Agent 客户端库
│   ├── __init__.py          # 导出 AgoraClient/AgoraConfig
│   ├── client.py            # HTTP + WebSocket 客户端
│   ├── config.py            # 客户端配置
│   └── ws_pool.py           # WS 连接池 + 自动重连
├── tests/                   # 测试（60+ 文件）
└── docs/                    # 设计文档
```

## 演进阶段与核心模块

| Phase | 主题 | 核心模块 | 说明 |
|-------|------|---------|------|
| 1 | MVP 基础 | main, config, models, state, router, ws, storage | 基本讨论+投票流程 |
| 2 | 智能讨论 | assessment, consensus_jump, devils_advocate, focus, dynamic_rounds, smart_scheduler, realtime_evaluator, voting/* | 实时评估+高级投票 |
| 3 | 记忆进化 | curator, memory_sync, history_pattern, similar_topic, judgment_tracker | 讨论经验沉淀+策略优化 |
| 4 | 自举系统 | bootstrap/* | Agora 讨论 Agora 自身 |
| 5 | 容错安全 | heartbeat, timeout, deadlock_prevention, input_validation, rate_limiter | 连接监控+输入防护 |
| 6 | 质量增强 | quality_guard, quality_scorer, perspective_ensurer, role_assigner, model_capabilities | 质量守卫+多模型差异 |

## 模块关系图

```
                          ┌─────────┐
                          │ main.py │ (FastAPI 入口)
                          └────┬────┘
                 ┌─────────────┼─────────────┐
                 ↓             ↓              ↓
           ┌──────────┐  ┌─────────┐  ┌──────────────┐
           │ router.py│  │ ws_ep.py│  │ bootstrap/*  │
           │(REST API)│  │(WS 端点)│  │(自举路由)     │
           └─────┬────┘  └────┬────┘  └──────┬───────┘
                 │            │               │
                 ↓            ↓               ↓
           ┌──────────┐  ┌──────────────┐  ┌────────────┐
           │ state.py │  │ ws_handlers  │  │ approval_  │
           │(状态机)   │  │ ws_vote      │  │ flow.py    │
           └─────┬────┘  │ ws_smart     │  └────────────┘
                 │       └──────┬───────┘
                 │              │
    ┌────────────┼──────────────┼─────────────────┐
    ↓            ↓              ↓                 ↓
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
│storage │ │assessment│ │ voting/*     │ │ curator     │
│(SQLite)│ │consensus │ │(投票子系统)   │ │(策略优化)    │
│        │ │devils_adv│ │              │ │memory_sync  │
│        │ │focus     │ │              │ │history_pat  │
│        │ │quality*  │ │              │ │similar_topic│
│        │ │role_assign│ │              │ │judgment_trk │
│        │ │heartbeat │ │              │ └─────────────┘
│        │ │timeout   │ │              │
│        │ │deadlock  │ │              │
│        │ │rate_limit│ │              │
│        │ │input_val │ │              │
└────────┘ └──────────┘ └──────────────┘
```

## 讨论状态机

```
draft ──(start)──→ discussing ──(start_voting)──→ voting ──(all_voted)──→ closed
                       │                              ↑
                  (assess)                            │
                       ↓                              │
                   assessing ──(start_voting)──────────┘
                       │           ↑
            (needs_devils_advocate) │
                       ↓           │
                devils_advocate ────┘
              (devils_advocate_done → discussing)
```

## 关键设计决策

1. **双协议通信**：REST API 用于 CRUD（创建议题、查结果），WebSocket 用于实时交互（发言、投票）
2. **状态机驱动**：所有状态转换通过 StateMachine 统一管理，确保转换合法性
3. **投票策略模式**：voting/ 子系统通过 factory.py 按方法名创建投票策略实例
4. **存储分层**：storage/ 按实体拆分模块（motions, votes, agents 等），统一通过 Storage 类访问
5. **进化闭环**：curator 分析讨论结果，优化后续调度策略（何时推进投票、追问关键点）
6. **客户端自动重连**：ws_pool.py 实现指数退避重连 + 请求-响应匹配
