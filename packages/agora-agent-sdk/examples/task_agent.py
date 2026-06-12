"""Task agent — executes tasks assigned by Agora Coordinator.

Demonstrates task execution lifecycle:
- report_task_start
- report_task_progress
- report_task_complete / report_task_failed
"""
import asyncio
import logging
import random

from agora_agent_sdk import (
    AgoraAgentClient,
    AgentConnectionConfig,
    AbstractBridge,
    TaskNode,
)

logging.basicConfig(level=logging.INFO)


class TaskBridge(AbstractBridge):
    """Bridge that executes assigned tasks."""

    async def on_task_assigned(self, task: TaskNode) -> None:
        """Execute a task and report progress."""
        print(f"[TASK] Starting: {task.title}")
        await self.client.report_task_start(task.id)

        # Simulate work with progress updates
        for i in range(1, 4):
            await asyncio.sleep(1)
            progress = i / 3.0
            print(f"[TASK] Progress: {progress:.0%}")
            await self.client.report_task_progress(task.id, progress)

        # Random success/failure for demo
        if random.random() > 0.2:
            print(f"[TASK] Completed: {task.title}")
            await self.client.report_task_complete(
                task.id, artifacts=["result.txt"]
            )
        else:
            print(f"[TASK] Failed: {task.title}")
            await self.client.report_task_failed(
                task.id, error="Simulated failure"
            )

    async def on_discussion_message(
        self, motion_id: str, content: str
    ) -> None:
        print(f"[DISCUSSION] Ignoring: {content[:40]}...")


async def main() -> None:
    config = AgentConnectionConfig(
        coordinator_url="http://localhost:8765",
        agent_name="task-agent",
        agent_type="custom",
        capabilities=["task-execution"],
    )
    client = AgoraAgentClient(config)
    bridge = TaskBridge(client)
    client.set_bridge(bridge)

    result = await client.register()
    print(f"Registered: {result.agent_id}")

    await client.connect()
    print("Waiting for task assignments...")
    try:
        await client.run()
    except KeyboardInterrupt:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
