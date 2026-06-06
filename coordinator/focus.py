"""Disagreement focus module for the Agora Coordinator.

Identifies under-represented stances in discussion and generates
focus prompts to encourage more balanced debate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Stance

if TYPE_CHECKING:
    from .storage import Storage


class DisagreementFocus:
    """Identifies unresolved disagreement points in discussions."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    async def identify_unresolved_points(
        self, motion_id: str
    ) -> list[str]:
        """Identify stances with less than 20% representation."""
        messages = await self.storage.get_messages(motion_id)

        by_stance: dict[Stance, list[dict]] = {
            Stance.SUPPORT: [],
            Stance.OPPOSE: [],
            Stance.NEUTRAL: [],
        }

        for msg in messages:
            stance = msg.get("stance")
            if isinstance(stance, Stance):
                by_stance[stance].append(msg)

        total = sum(len(v) for v in by_stance.values())
        if total == 0:
            return []

        unresolved: list[str] = []
        for stance, msgs in by_stance.items():
            if len(msgs) / total < 0.2:
                unresolved.append(f"需要更多{stance.value}观点")

        return unresolved

    async def generate_focus_prompt(self, motion_id: str) -> str:
        """Generate a focus prompt based on unresolved points."""
        unresolved = await self.identify_unresolved_points(motion_id)

        if not unresolved:
            return "请继续讨论，提出你的最终观点。"

        return (
            "当前讨论存在以下分歧点，请重点讨论：\n"
            + "\n".join(f"- {p}" for p in unresolved)
        )
