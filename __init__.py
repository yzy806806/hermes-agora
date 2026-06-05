"""Hermes Agora — Multi-Agent Deliberation Plugin.

A Hermes plugin that enables structured discussion, negotiation, and voting
among multiple Hermes Agents. Each participant is a full Hermes instance with
memory, skills, and self-evolution capabilities.
"""

from __future__ import annotations

import logging

from agent_client import AgoraClient, AgoraConfig, load_config

logger = logging.getLogger(__name__)

# Module-level client singleton — initialized in register()
_client: AgoraClient | None = None


def _get_client() -> AgoraClient:
    """Return the global AgoraClient, raising if not initialized."""
    if _client is None:
        raise RuntimeError("Agora plugin not registered — call register() first")
    return _client


# -----------------------------------------------------------------------
# Tool Implementations
# -----------------------------------------------------------------------


async def agora_create_motion(
    title: str,
    description: str = "",
    context: str | None = None,
    rounds: int | None = None,
    voting_method: str = "simple_majority",
) -> dict:
    """Create a new discussion motion/topic."""
    return await _get_client().create_motion(
        title=title, description=description, context=context,
        rounds=rounds, voting_method=voting_method,
    )


async def agora_speak(
    motion_id: str,
    content: str,
    stance: str = "neutral",
    evidence: list[dict] | None = None,
) -> dict:
    """Submit a speech/opinion in a discussion via WebSocket."""
    return await _get_client().speak(
        motion_id=motion_id, content=content, stance=stance, evidence=evidence,
    )


async def agora_vote(
    motion_id: str,
    vote: str,
    reason: str = "",
    confidence: float = 0.5,
) -> dict:
    """Cast a vote on a motion via WebSocket."""
    return await _get_client().vote(
        motion_id=motion_id, vote=vote, reason=reason, confidence=confidence,
    )


async def agora_list_motions(
    status: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    """List discussion motions from the Coordinator."""
    return await _get_client().list_motions(
        status=status, limit=limit, offset=offset,
    )


async def agora_get_history(
    motion_id: str,
    limit: int = 50,
    include_votes: bool = True,
) -> dict:
    """Get discussion history for a motion."""
    return await _get_client().get_history(
        motion_id=motion_id, limit=limit, include_votes=include_votes,
    )


async def agora_get_result(motion_id: str) -> dict:
    """Get the final result of a discussion/vote."""
    return await _get_client().get_result(motion_id=motion_id)


# -----------------------------------------------------------------------
# Hook Handlers
# -----------------------------------------------------------------------


async def on_session_start(ctx) -> None:
    """Hook: Agent上线时向Coordinator注册。"""
    logger.info("Agora: Agent session starting")


async def on_session_end(ctx) -> None:
    """Hook: 讨论经验写入memory。"""
    logger.info("Agora: Agent session ending")


async def post_tool_call(ctx, tool_name: str, tool_input: dict, tool_output: dict) -> None:
    """Hook: 记录讨论中的工具使用作为证据。"""
    pass


# -----------------------------------------------------------------------
# Plugin Registration
# -----------------------------------------------------------------------


def register(ctx) -> None:
    """Register Agora plugin with Hermes."""
    global _client
    logger.info("Registering Hermes Agora plugin")

    # Load config from Hermes context if available
    hermes_cfg = {}
    if hasattr(ctx, "config"):
        hermes_cfg = ctx.config if isinstance(ctx.config, dict) else {}
    config = load_config(hermes_cfg)
    _client = AgoraClient(config)

    # Register tools
    ctx.register_tool("agora_create_motion", agora_create_motion)
    ctx.register_tool("agora_speak", agora_speak)
    ctx.register_tool("agora_vote", agora_vote)
    ctx.register_tool("agora_list_motions", agora_list_motions)
    ctx.register_tool("agora_get_history", agora_get_history)
    ctx.register_tool("agora_get_result", agora_get_result)

    # Register hooks
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("post_tool_call", post_tool_call)

    # Register slash command
    from commands import handle_agora
    ctx.register_command(
        "agora",
        handle_agora,
        description="多 Agent 讨论决策",
        args_hint="<new|list|status|vote|result> [args]",
    )

    logger.info("Hermes Agora plugin registered successfully")
