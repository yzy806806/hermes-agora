"""Slash command handler for /agora.

Dispatches to subcommand modules:
  /agora              — status overview
  /agora new <title>  — create motion + start discussion
  /agora list         — list active motions
  /agora status <id>  — show motion detail
  /agora vote <id> <yes|no|abstain> — cast a vote
  /agora result <id>  — get final decision result
"""

from __future__ import annotations

import asyncio
import logging
import shlex

logger = logging.getLogger(__name__)

_SUBCOMMANDS = {
    "new": "cmd_new",
    "list": "cmd_list",
    "status": "cmd_status",
    "vote": "cmd_vote",
    "result": "cmd_result",
}


async def _dispatch(subcmd: str, args: str) -> str:
    """Import subcommand module and call its handler."""
    mod_name = _SUBCOMMANDS.get(subcmd)
    if mod_name is None:
        return _help_text()
    import importlib
    mod = importlib.import_module(mod_name)
    handler = getattr(mod, f"handle_{subcmd}")
    return await handler(args)


def _help_text() -> str:
    """Return usage help for /agora."""
    return (
        "\U0001f3db\ufe0f /agora \u7528\u6cd5:\n"
        "  /agora              \u72b6\u6001\u603b\u89c8\n"
        "  /agora new <\u6807\u9898>  \u521b\u5efa\u8bae\u9898\n"
        "  /agora list         \u5217\u51fa\u8bae\u9898\n"
        "  /agora status <id>  \u67e5\u770b\u72b6\u6001\n"
        "  /agora vote <id> <yes|no|abstain>  \u6295\u7968\n"
        "  /agora result <id>  \u83b7\u53d6\u7ed3\u679c"
    )


async def handle_agora(raw_args: str) -> str:
    """Main handler for /agora slash command.

    Signature matches PluginContext.register_command:
    fn(raw_args: str) -> str | None
    """
    raw_args = raw_args.strip()

    if not raw_args:
        # Overview mode
        from __init__ import agora_list_motions
        try:
            data = await agora_list_motions(limit=5)
        except Exception as exc:
            return f"\u274c \u65e0\u6cd5\u8fde\u63a5 Coordinator: {exc}"
        motions = data.get("motions", [])
        from cmd_new import _icon
        lines = ["\U0001f3db\ufe0f Agora \u72b6\u6001\u603b\u89c8", "=" * 30]
        if not motions:
            lines.append("\u5f53\u524d\u65e0\u6d3b\u8dc3\u8bae\u9898")
        else:
            for m in motions:
                st = m.get("status", "unknown")
                lines.append(
                    f"  {_icon(st)} {m.get('title', '?')} "
                    f"[{m.get('id', '?')[:8]}] {st}"
                )
        lines.append("")
        lines.append("\u7528\u6cd5: /agora new|list|status|vote|result")
        return "\n".join(lines)

    # Parse subcommand
    parts = raw_args.split(None, 1)
    subcmd = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if subcmd in ("help", "h", "?"):
        return _help_text()

    return await _dispatch(subcmd, rest)
