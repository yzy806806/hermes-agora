# Agora CLI Bridge

Connect CLI-based agents (Codex, Claude Code, OpenClaw, etc.) to Agora Coordinator via PTY subprocess management.

## Installation

```bash
pip install agora-cli-bridge
```

## Quick Start

```python
from agora_cli_bridge import PtyManager, BaseAdapter

manager = PtyManager()
proc = await manager.spawn_agent("my-agent", ["codex", "chat"])
```

## License

MIT
