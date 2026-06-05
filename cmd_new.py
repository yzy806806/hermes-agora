"""Subcommand handlers for /agora slash command.

Each handler is an async function that returns a formatted string.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_STATUS_ICONS = {
    "draft": "\U0001f4dd",
    "discussing": "\U0001f4ac",
    "voting": "\U0001f5f3\ufe0f",
    "closed": "\u2705",
}


def _icon(status: str) -> str:
    return _STATUS_ICONS.get(status, "\u2753")


async def handle_new(args: str) -> str:
    """Create a new motion: /agora new <title> [options]."""
    from __init__ import agora_create_motion

    if not args.strip():
        return (
            "\u274c \u7528\u6cd5: /agora new <\u6807\u9898> "
            "[-d \u63cf\u8ff0] [-r \u8f6e\u6570] "
            "[-v \u6295\u7968\u65b9\u5f0f]"
        )

    parts = args.strip().split(None, 1)
    title = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    description = ""
    rounds = None
    voting_method = "simple_majority"

    # Simple option parsing
    tokens = rest.split()
    i = 0
    while i < len(tokens):
        if tokens[i] in ("-d", "--description") and i + 1 < len(tokens):
            description = tokens[i + 1]
            i += 2
        elif tokens[i] in ("-r", "--rounds") and i + 1 < len(tokens):
            try:
                rounds = int(tokens[i + 1])
            except ValueError:
                return f"\u274c \u8f6e\u6570\u5fc5\u987b\u662f\u6574\u6570: {tokens[i+1]}"
            i += 2
        elif tokens[i] in ("-v", "--voting") and i + 1 < len(tokens):
            voting_method = tokens[i + 1]
            i += 2
        else:
            i += 1

    try:
        result = await agora_create_motion(
            title=title, description=description,
            rounds=rounds, voting_method=voting_method,
        )
    except Exception as exc:
        return f"\u274c \u521b\u5efa\u8bae\u9898\u5931\u8d25: {exc}"

    mid = result.get("id", "?")
    return (
        f"\U0001f3af \u8bae\u9898\u5df2\u521b\u5efa: {title}\n"
        f"\U0001f194 ID: {mid}\n"
        f"\U0001f4ca \u72b6\u6001: \u7b49\u5f85\u53c2\u4e0e\u8005...\n\n"
        f"/agora status {mid}\n"
        f"/agora result {mid}"
    )
