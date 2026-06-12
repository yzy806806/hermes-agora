"""Discussion agent — participates in Agora discussions.

Creates a motion, speaks on it, and votes. Demonstrates
the discussion API: create_motion, speak, vote.
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


class DiscussionBridge(AbstractBridge):
    """Bridge that actively participates in discussions."""

    async def on_task_assigned(self, task: TaskNode) -> None:
        print(f"[TASK] Ignoring task: {task.title}")

    async def on_discussion_message(
        self, motion_id: str, content: str
    ) -> None:
        """Respond to discussion messages from other agents."""
        print(f"[DISCUSSION] Heard: {content[:60]}...")
        # Speak in response
        await self.client.speak(
            motion_id,
            "I agree with the previous point. "
            "Let's proceed with the proposed approach.",
        )
        # Cast a vote
        await self.client.vote(motion_id, "approve")
        print(f"[VOTE] Voted 'approve' on {motion_id}")


async def main() -> None:
    config = AgentConnectionConfig(
        coordinator_url="http://localhost:8765",
        agent_name="discussion-agent",
        agent_type="custom",
        capabilities=["discussion"],
    )
    client = AgoraAgentClient(config)
    bridge = DiscussionBridge(client)
    client.set_bridge(bridge)

    result = await client.register()
    print(f"Registered: {result.agent_id}")

    # Create a motion to start a discussion
    motion = await client.create_motion(
        "Adopt async-first architecture",
        desc="Proposal to make all agent APIs async by default.",
    )
    print(f"Created motion: {motion.get('motion_id', '?')}")

    await client.connect()
    try:
        await client.run()
    except KeyboardInterrupt:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
