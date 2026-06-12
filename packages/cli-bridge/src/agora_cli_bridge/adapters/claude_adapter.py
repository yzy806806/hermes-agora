"""Claude Code adapter for CLI Bridge.

Parses MCP (Model Context Protocol) over stdio and maps
tool calls to Agora format.

Claude Code uses JSON-RPC 2.0 over stdio for tool communication.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from .base import BaseCLIAdapter, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseCLIAdapter):
    """Adapter for Claude Code CLI agent (MCP over stdio).

    Claude Code communicates via JSON-RPC 2.0 messages:
    - Request: {"jsonrpc":"2.0","method":"tools/call","params":{...},"id":1}
    - Response: {"jsonrpc":"2.0","result":{...},"id":1}
    """

    agent_type = "claude"

    def parse_output(self, raw: bytes) -> list[ToolCall]:
        """Parse MCP JSON-RPC messages into ToolCall list."""
        calls: list[ToolCall] = []
        text = raw.decode("utf-8", errors="replace")
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            call = self._parse_rpc(obj)
            if call:
                calls.append(call)
        return calls

    def _parse_rpc(self, obj: dict[str, Any]) -> ToolCall | None:
        """Parse a JSON-RPC request into a ToolCall."""
        if obj.get("jsonrpc") != "2.0":
            return None
        method = obj.get("method", "")
        if method != "tools/call":
            return None
        params = obj.get("params", {})
        call_id = str(obj.get("id", uuid.uuid4().hex[:8]))
        name = params.get("name", "")
        arguments = params.get("arguments", params.get("input", {}))
        return ToolCall(
            call_id=call_id,
            name=name,
            arguments=arguments,
            raw=json.dumps(obj),
        )

    def format_result(self, result: ToolResult) -> bytes:
        """Format ToolResult as MCP JSON-RPC response."""
        content: list[dict[str, str]] = [
            {"type": "text", "text": result.output}
        ]
        if result.error:
            payload: dict[str, Any] = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": result.error},
                "id": result.call_id,
            }
        else:
            payload = {
                "jsonrpc": "2.0",
                "result": {"content": content},
                "id": result.call_id,
            }
        return (json.dumps(payload) + "\n").encode("utf-8")

    def is_tool_call(self, line: bytes) -> bool:
        """Check if line is an MCP tools/call request."""
        try:
            obj = json.loads(line)
            return (
                obj.get("jsonrpc") == "2.0"
                and obj.get("method") == "tools/call"
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False
