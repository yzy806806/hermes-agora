"""/agora vote subcommand handler."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_VALID_VOTES = {"yes", "no", "abstain"}


async def handle_vote(args: str) -> str:
    """Cast a vote: /agora vote <motion_id> <yes|no|abstain> [reason]."""
    from __init__ import agora_vote

    parts = args.strip().split(None, 2)
    if len(parts) < 2:
        return (
            "\u274c \u7528\u6cd5: /agora vote <motion_id> "
            "<yes|no|abstain> [\u7406\u7531]"
        )

    motion_id = parts[0]
    vote_choice = parts[1].lower()
    reason = parts[2] if len(parts) > 2 else ""

    if vote_choice not in _VALID_VOTES:
        return (
            f"\u274c \u65e0\u6548\u6295\u7968\u9009\u9879: {vote_choice}\n"
            f"\u53ef\u9009: {', '.join(_VALID_VOTES)}"
        )

    try:
        result = await agora_vote(
            motion_id=motion_id, vote=vote_choice, reason=reason,
        )
    except Exception as exc:
        return f"\u274c \u6295\u7968\u5931\u8d25: {exc}"

    status = result.get("status", "unknown")
    total = result.get("total_votes", "?")
    return (
        f"\U0001f5f3\ufe0f \u6295\u7968\u5df2\u63d0\u4ea4: {vote_choice}\n"
        f"\U0001f194 \u8bae\u9898: {motion_id}\n"
        f"\U0001f4ca \u72b6\u6001: {status} | \u5df2\u6295: {total}"
    )
