# Hermes Agora 开发计划

## Phase 1: 最小可用（MVP）

目标：能跑通一轮完整的讨论流程

- [ ] 项目骨架：plugin.yaml + __init__.py + register(ctx)
- [ ] Coordinator FastAPI 服务（HTTP + WebSocket）
- [ ] SQLite 存储层（motions、messages、votes）
- [ ] 6 个基础工具（create_motion、speak、vote、list、history、result）
- [ ] /agora 斜杠命令
- [ ] Agent 注册/注销
- [ ] 单轮讨论 + 简单多数投票

## Phase 2: 智能讨论

目标：讨论质量提升，不只是机械轮次

- [ ] Coordinator 智能判断讨论是否充分（不再固定N轮）
  - 达成共识 → 提前投票
  - 分歧大 → 继续讨论
  - 跑偏 → 拉回正题
- [ ] 魔鬼代言人机制（强制引入反对意见）
- [ ] 分歧点聚焦（只继续讨论未达成共识的点）
- [ ] 多种投票方式：simple_majority / supermajority / unanimous / weighted
- [ ] 非二元选择（A方案/B方案/C方案、优先级排序）

## Phase 3: 记忆与进化

目标：讨论越多越聪明

- [ ] 讨论结论自动写入 Hermes memory
- [ ] Coordinator 记住历史决策模式
- [ ] Participant 记住自己的判断正确率
- [ ] Curator 优化讨论策略
- [ ] 相似议题自动引用历史结论（不重复讨论）

## Phase 4: 自举

目标：用 Agora 开发 Agora

- [ ] AI 团队通过 Agora 讨论开发方向
- [ ] 用户拍板 + AI 团队方案论证
- [ ] 开发计划由讨论结果驱动
- [ ] 项目自组织、自进化

## 待讨论的设计问题

1. **讨论质量保证**：如何确保讨论不流于形式？魔鬼代言人角色如何实现？
2. **效率优化**：达成共识的点跳过，只讨论分歧点？动态轮次？
3. **记忆检索**：相似议题的判定标准？历史结论的引用方式？
4. **讨论终止条件**：谁来判断"讨论够了"？Coordinator？用户？
5. **投票设计**：非二元选择怎么做？加权投票的权重怎么定？
6. **多模型差异利用**：不同模型天然有不同观点，如何最大化利用？
7. **容错机制**：某个 Agent 掉线怎么办？讨论超时怎么办？
8. **安全性**：防止某个 Agent 垄断讨论？防止合谋？
