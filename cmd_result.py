"""/agora result subcommand handler."""

from __future__ import annotations

import logging

from cmd_new import _icon

logger = logging.getLogger(__name__)


async def handle_result(args: str) -> str:
    """Get motion result: /agora result <motion_id>."""
    from __init__ import agora_get_result

    motion_id = args.strip()
    if not motion_id:
        return "\u274c \u7528\u6cd5: /agora result <motion_id>"

    try:
        data = await agora_get_result(motion_id=motion_id)
    except Exception as exc:
        return f"\u274c \u83b7\u53d6\u7ed3\u679c\u5931\u8d25: {exc}"

    title = data.get("title", "?")
    status = data.get("status", "closed")
    decision = data.get("decision", "pending")

    lines = [
        f"{_icon(status)} \u8bae\u9898\u5df2\u7ed3\u675f: {title}",
        "",
        "\u6295\u7968\u7ed3\u679c:",
    ]

    votes = data.get("votes", {})
    yes_count = votes.get("yes", 0)
    no_count = votes.get("no", 0)
    abstain_count = votes.get("abstain", 0)
    total = yes_count + no_count + abstain_count

    if total > 0:
        lines.append(
            f"  \u2705 \u8d5e\u6210: {yes_count} "
            f"({yes_count/total*100:.1f}%)"
        )
        lines.append(
            f"  \u274c \u53cd\u5bf9: {no_count} "
            f"({no_count/total*100:.1f}%)"
        )
        lines.append(f"  \u23f8\ufe0f \u5f03\u6743: {abstain_count}")
    else:
        lines.append("  \u65e0\u6295\u7968\u6570\u636e")

    outcome = "\u901a\u8fc7" if decision == "passed" else "\u5426\u51b3"
    lines.append(f"\n\U0001f3c1 \u51b3\u7b56: {outcome}")

    rationale = data.get("rationale", "")
    if rationale:
        lines.append(f"\n\u7406\u7531: {rationale[:200]}")

    return "\n".join(lines)
