"""Minimal agent — connects to Agora and logs events.

Run: python -m examples.minimal_agent
Requires a running Agora Coordinator on localhost:8765.
"""
import asyncio
import logging

from agora_agent_sdk import (
    AgoraAgentClient,
    AgentConnectionConfig,
    AbstractBridge,
    TaskNode,
)

logging.basicConfig(level=logging.INFO)


class MinimalBridge(AbstractBridge):
    """Simple bridge that logs task assignments and discussions."""

    async def on_task_assigned(self, task: TaskNode) -> None:
        print(f"[TASK] {task.title} (id={task.id})")

    async def on_discussion_message(
        self, motion_id: str, content: str
    ) -> None:
        print(f"[DISCUSSION] motion={motion_id}: {content[:80]}")


async def main() -> None:
    config = AgentConnectionConfig(
        coordinator_url="http://localhost:8765",
        agent_name="minimal-agent",
        agent_type="custom",
        capabilities=["task-execution"],
    )
    client = AgoraAgentClient(config)
    bridge = MinimalBridge(client)
    client.set_bridge(bridge)

    print("Registering with Agora Coordinator...")
    result = await client.register()
    print(f"Registered: agent_id={result.agent_id}")

    print("Connecting via WebSocket...")
    await client.connect()
    print("Connected! Listening for events...")

    try:
        await client.run()
    except KeyboardInterrupt:
        await client.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
