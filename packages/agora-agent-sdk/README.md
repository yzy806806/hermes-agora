# Agora Agent SDK

Lightweight Python SDK for connecting agents to
[Agora](https://github.com/yzy806806/agora) Coordinator.
Only `httpx` + `pydantic` — no Agora package needed.

## Installation

```bash
pip install agora-agent-sdk        # production
pip install agora-agent-sdk[dev]   # with pytest
```

## Quick Start

```python
import asyncio
from agora_agent_sdk import (
    AgoraAgentClient, AgentConnectionConfig, AbstractBridge, TaskNode,
)

class MyBridge(AbstractBridge):
    async def on_task_assigned(self, task: TaskNode) -> None:
        print(f"Got task: {task.title}")
    async def on_discussion_message(self, mid: str, content: str) -> None:
        print(f"Discussion: {content[:60]}")

async def main():
    config = AgentConnectionConfig(
        agent_name="my-agent", agent_type="custom",
        capabilities=["task-execution"],
    )
    client = AgoraAgentClient(config)
    bridge = MyBridge(client)
    client.set_bridge(bridge)
    await client.register()
    await client.connect()
    await client.run()

asyncio.run(main())
```

## API Reference

**AgoraAgentClient** — `register()` `connect()` `disconnect()` `run()` `set_bridge()`
`create_motion(title, desc)` `speak(motion_id, content)` `vote(motion_id, choice)`
`report_task_start(id)` `report_task_progress(id, pct)` `report_task_complete(id, artifacts)` `report_task_failed(id, error)`

**AgentConnectionConfig** — `coordinator_url` (default `http://localhost:8765`),
`agent_name`, `agent_type` (`custom`/`hermes`/`cli`/`docker`),
`capabilities`, `model`, `heartbeat_interval` (30), `max_retries` (3).

**AbstractBridge** — implement `on_task_assigned(task)` and
`on_discussion_message(motion_id, content)`. Optional:
`on_devils_advocate(motion_id, topic)`. Lifecycle: `start()`, `stop()`.

**SessionStore** — file-based session persistence:
```python
from agora_agent_sdk import SessionStore, SessionRecord
store = SessionStore(".sessions")
record = SessionRecord(agent_id="agent-1", session_type="task_execution")
store.save(record)
store.list_sessions(agent_id="agent-1")
```

## Examples

`examples/minimal_agent.py` — event listener
`examples/discussion_agent.py` — discussion + voting
`examples/task_agent.py` — task execution with progress

## License
MIT