"""/agora status subcommand handler."""

from __future__ import annotations

import logging

from cmd_new import _icon

logger = logging.getLogger(__name__)


async def handle_status(args: str) -> str:
    """Show motion status: /agora status <motion_id>."""
    from __init__ import agora_list_motions, agora_get_history

    motion_id = args.strip()
    if not motion_id:
        return "\u274c \u7528\u6cd5: /agora status <motion_id>"

    try:
        hist = await agora_get_history(
            motion_id=motion_id, limit=20, include_votes=True,
        )
    except Exception as exc:
        return f"\u274c \u83b7\u53d6\u8bae\u9898\u72b6\u6001\u5931\u8d25: {exc}"

    title = hist.get("title", "?")
    status = hist.get("status", "unknown")
    current_round = hist.get("current_round", "?")
    total_rounds = hist.get("total_rounds", "?")
    participants = hist.get("participants", [])

    lines = [
        f"\U0001f4cb \u8bae\u9898: {title}",
        f"\U0001f194 ID: {motion_id}",
        f"\U0001f4ca \u72b6\u6001: {_icon(status)} {status}",
    ]

    if isinstance(current_round, int) and isinstance(total_rounds, int):
        lines.append(
            f"\U0001f504 \u8fdb\u5ea6: "
            f"\u7b2c {current_round} \u8f6e / {total_rounds} \u8f6e"
        )

    if participants:
        names = ", ".join(
            p.get("name", p.get("id", "?")) if isinstance(p, dict) else str(p)
            for p in participants
        )
        lines.append(f"\U0001f465 \u53c2\u4e0e\u8005: {names}")

    # Show recent speeches
    speeches = hist.get("speeches", [])
    if speeches:
        lines.append("")
        lines.append("\u6700\u8fd1\u53d1\u8a00:")
        for s in speeches[-5:]:
            agent = s.get("agent_id", "?")
            stance = s.get("stance", "neutral")
            content = s.get("content", "")[:60]
            lines.append(f"  {stance} {agent}: {content}")

    if status == "voting":
        lines.append("")
        lines.append("\U0001f5f3\ufe0f \u6295\u7968\u4e2d:")
        lines.append(f"  /agora vote {motion_id} yes")
        lines.append(f"  /agora vote {motion_id} no")
        lines.append(f"  /agora vote {motion_id} abstain")

    return "\n".join(lines)
