# Hermes Agora - Phase 1 骨架

## 产出

### 1. plugin.yaml

```yaml
name: agora
version: "0.1.0"
description: "Multi-Agent Deliberation Plugin for Hermes..."
author: yzy806806
kind: backend
provides_tools:
  - agora_create_motion
  - agora_speak
  - agora_vote
  - agora_list_motions
  - agora_get_history
  - agora_get_result
hooks:
  - on_session_start
  - on_session_end
  - post_tool_call
```

### 2. __init__.py

包含:
- register(ctx) 函数 - 注册所有 tools 和 hooks
- 6 个 Tool stubs (TODO for Phase 2)
- 3 个 Hook stubs (TODO for Phase 2)

## 安装验证

```bash
hermes plugins install /root/hermes-agora --enable
hermes plugins list
```

## 下一步 (Phase 2)

实现:
1. Coordinator WebSocket 服务器
2. Participant 客户端
3. 状态管理 (SQLite)
4. 工具实际逻辑
5. 生命周期钩子实际逻辑