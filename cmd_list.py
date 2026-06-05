"""/agora list subcommand handler."""

from __future__ import annotations

import logging

from cmd_new import _icon

logger = logging.getLogger(__name__)


async def handle_list(args: str) -> str:
    """List motions: /agora list [--all] [--status X] [--limit N]."""
    from __init__ import agora_list_motions

    status_filter = None
    limit = 10
    show_all = False

    tokens = args.strip().split()
    i = 0
    while i < len(tokens):
        if tokens[i] in ("-a", "--all"):
            show_all = True
            i += 1
        elif tokens[i] in ("-s", "--status") and i + 1 < len(tokens):
            status_filter = tokens[i + 1]
            i += 2
        elif tokens[i] in ("-l", "--limit") and i + 1 < len(tokens):
            try:
                limit = int(tokens[i + 1])
            except ValueError:
                return f"\u274c limit \u5fc5\u987b\u662f\u6574\u6570: {tokens[i+1]}"
            i += 2
        else:
            i += 1

    if not show_all and status_filter is None:
        status_filter = "discussing"

    try:
        data = await agora_list_motions(
            status=status_filter, limit=limit,
        )
    except Exception as exc:
        return f"\u274c \u83b7\u53d6\u8bae\u9898\u5217\u8868\u5931\u8d25: {exc}"

    motions = data.get("motions", [])
    if not motions:
        return "\U0001f4cb \u5f53\u524d\u65e0\u8bae\u9898"

    lines = ["\U0001f4cb \u8bae\u9898\u5217\u8868", "-" * 30]
    for m in motions:
        st = m.get("status", "unknown")
        lines.append(
            f"  {_icon(st)} {m.get('title', '?')} "
            f"[{m.get('id', '?')[:8]}] {st}"
        )
    return "\n".join(lines)
