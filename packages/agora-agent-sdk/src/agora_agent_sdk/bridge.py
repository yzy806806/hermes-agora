"""AbstractBridge ABC — base class for platform bridges.

Each platform (Hermes, CLI, Docker) implements this ABC.
The bridge translates platform-specific tool calls into Agora
WS messages, and vice versa.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AgoraAgentClient
    from .protocol import TaskNode


class AbstractBridge(ABC):
    """Bridge between an agent runtime and AgoraAgentClient.

    Subclasses implement platform-specific logic for handling
    task assignments, discussion messages, and devil's advocate
    requests from the Agora Coordinator.
    """

    def __init__(self, client: AgoraAgentClient) -> None:
        self.client = client

    @abstractmethod
    async def on_task_assigned(self, task: TaskNode) -> None:
        """Called when a TASK_ASSIGNED message arrives.

        Should start executing the task on the platform.
        """
        ...

    @abstractmethod
    async def on_discussion_message(
        self, motion_id: str, content: str
    ) -> None:
        """Called when a discussion message arrives (e.g. SPEECH_ADDED).

        The agent's turn to speak in a discussion.
        """
        ...

    @abstractmethod
    async def on_devils_advocate(
        self, motion_id: str, topic: str
    ) -> str:
        """Called when coordinator requests a devil's advocate response.

        Should return the agent's counter-argument.
        """
        ...

    async def start(self) -> None:
        """Default lifecycle: register, connect, run."""
        await self.client.register()
        await self.client.connect()
        await self.client.run()

    async def stop(self) -> None:
        """Disconnect from coordinator."""
        await self.client.disconnect()
