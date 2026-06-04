# Hermes Agora 项目结构

hermes-agora/
├── README.md
├── docs/
│   └── PROTOCOL.md          # 通信协议规范
├── coordinator/             # 调度中心服务
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── models.py            # 数据模型
│   ├── router.py            # API 路由
│   ├── ws.py                # WebSocket 处理
│   ├── state.py             # 讨论状态机
│   ├── storage.py           # SQLite 存储
│   └── config.py            # 配置
├── agent_client/            # Agent 客户端库
│   ├── __init__.py
│   ├── client.py            # WebSocket 客户端
│   ├── hermes_bridge.py     # 对接 Hermes CLI/API
│   └── memory_sync.py       # 讨论经验写入 memory
├── tests/
│   ├── test_coordinator.py
│   ├── test_agent_client.py
│   └── test_integration.py
├── pyproject.toml
└── LICENSE
