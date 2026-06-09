"""WebSocket endpoint for the Agora Coordinator service.

Phase 8.2: Added tenant_id parameter for per-tenant isolation.
Routes messages through tenant-specific ConnectionHub.
"""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

from .input_validation import InputValidator
from .models import MessageType
from .observability.trace import set_trace_id
from .rate_limiter import RateLimiter
from .ws import manager
from .ws_handlers import handle_ping, handle_register, handle_speak
from .ws_vote import handle_vote

logger = logging.getLogger(__name__)

_validator = InputValidator()
_rate_limiter = RateLimiter()


async def websocket_endpoint(
    websocket: WebSocket, agent_id: str, tenant_id: str = "default",
) -> None:
    """FastAPI WebSocket endpoint at /ws/{agent_id}.

    Phase 8.2: tenant_id query param for multi-tenancy.
    Default is 'default' for backward compatibility.

    Args:
        websocket: FastAPI WebSocket connection object.
        agent_id: Unique identifier for the connecting agent.
        tenant_id: Tenant to connect under (default: "default").
    """
    hub = manager.get_hub(tenant_id)
    # Lazy-init deps for non-default tenants (Phase 8.2 fix)
    if hub._storage is None and tenant_id != "default":
        storage_mgr = getattr(websocket.app.state, "storage_mgr", None)
        if storage_mgr is not None:
            from .state import StateMachine
            storage = await storage_mgr.get_tenant_storage(tenant_id)
            sm = StateMachine(storage)
            manager.set_tenant_deps(tenant_id, storage, sm)
            logger.info("Lazy-init deps for tenant %s", tenant_id)
    if not await hub.connect(agent_id, websocket):
        return
    try:
        await hub.send(agent_id, {
            "type": MessageType.WELCOME,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
        })
        while True:
            data = await websocket.receive_text()
            await _route_message(agent_id, data, hub)
    except Exception:
        pass
    finally:
        hub.disconnect(agent_id)
        await on_agent_disconnect(agent_id, hub)


async def _route_message(agent_id: str, raw: str, hub) -> None:
    """Parse and route a WebSocket message to the appropriate handler."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await hub.send(agent_id, {
            "type": MessageType.ERROR,
            "payload": {"code": "invalid_json", "message": "Bad JSON"},
        })
        return

    msg_type = msg.get("type", "")
    payload = msg.get("payload", {})

    # Propagate trace_id from message into context var
    trace_id = msg.get("trace_id") or ""
    set_trace_id(trace_id)
    storage = hub._storage
    sm = hub._state_machine

    if storage is None or sm is None:
        logger.error("WS deps not initialized")
        return

    if msg_type == MessageType.PING:
        await handle_ping(agent_id, payload, hub)
    elif msg_type == MessageType.REGISTER:
        await handle_register(agent_id, payload, storage, hub)
    elif msg_type == MessageType.SPEAK:
        if not _rate_limiter.check_rate(agent_id, "speak"):
            await hub.send(agent_id, {
                "type": MessageType.ERROR,
                "payload": {"code": "rate_limited", "message": "Speak rate exceeded"},
            })
            return
        try:
            payload = _validator.validate_speak_payload(payload)
        except ValueError as exc:
            await hub.send(agent_id, {
                "type": MessageType.ERROR,
                "payload": {"code": "validation_error", "message": str(exc)},
            })
            return
        await handle_speak(agent_id, payload, storage, sm, hub)
    elif msg_type == MessageType.VOTE:
        if not _rate_limiter.check_rate(agent_id, "vote"):
            await hub.send(agent_id, {
                "type": MessageType.ERROR,
                "payload": {"code": "rate_limited", "message": "Vote rate exceeded"},
            })
            return
        try:
            payload = _validator.validate_vote_payload(payload)
        except ValueError as exc:
            await hub.send(agent_id, {
                "type": MessageType.ERROR,
                "payload": {"code": "validation_error", "message": str(exc)},
            })
            return
        await handle_vote(agent_id, payload, storage, sm, hub)
    elif msg_type == MessageType.DEVILS_ADVOCATE_RESPONSE:
        await _handle_devils_advocate_response(
            agent_id, payload, storage, sm, hub)
    elif msg_type == MessageType.TASK_STATUS:
        from .task_exec import handle_task_status
        await handle_task_status(agent_id, payload, storage, hub)
    elif msg_type == MessageType.TASK_ACCEPT_RESULT:
        from .task_exec import handle_task_accept_result
        await handle_task_accept_result(agent_id, payload, storage, hub)
    else:
        logger.warning("Unknown type from %s: %s", agent_id, msg_type)


async def _handle_devils_advocate_response(
    agent_id: str, payload: dict, storage, sm, hub,
) -> None:
    """Process devil's advocate response and store as a SPEAK message."""
    motion_id = payload.get("motion_id")
    if not motion_id:
        return
    content = payload.get("content", "")
    round_num = payload.get("round", 1)
    await storage.add_message(
        motion_id, agent_id, round_num, "oppose", content,
        [{"source": "devils_advocate"}],
    )
    await hub.broadcast({
        "type": MessageType.BROADCAST,
        "motion_id": motion_id,
        "agent_id": agent_id,
        "payload": {
            "round": round_num,
            "stance": "oppose",
            "content": content,
            "devils_advocate": True,
        },
    })


async def on_agent_disconnect(agent_id: str, hub) -> None:
    """Mark agent offline and notify others in the same tenant."""
    if hub._storage is not None:
        await hub._storage.set_agent_online(agent_id, False)
    await hub.broadcast({
        "type": MessageType.AGENT_OFFLINE,
        "agent_id": agent_id,
    })
    logger.info("Agent %s went offline", agent_id)
