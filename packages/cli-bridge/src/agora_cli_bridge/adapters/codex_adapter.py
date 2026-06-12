"""Codex (OpenAI) adapter for CLI Bridge.

Parses Codex JSON output format and maps tool calls to Agora format.
Codex emits structured JSON on stdout when using --format json.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from .base import BaseCLIAdapter, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class CodexAdapter(BaseCLIAdapter):
    """Adapter for OpenAI Codex CLI agent.

    Codex outputs JSON lines with tool calls like:
    {"type":"function_call","id":"...","name":"read_file","arguments":{...}}
    """

    agent_type = "codex"

    def parse_output(self, raw: bytes) -> list[ToolCall]:
        """Parse Codex JSON-lines output into ToolCall list."""
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
            call = self._parse_single(obj)
            if call:
                calls.append(call)
        return calls

    def _parse_single(self, obj: dict[str, Any]) -> ToolCall | None:
        """Parse one JSON object into a ToolCall."""
        obj_type = obj.get("type", "")
        if obj_type not in ("function_call", "tool_call"):
            return None
        call_id = obj.get("id", uuid.uuid4().hex[:8])
        name = obj.get("name", "")
        arguments = obj.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"raw": arguments}
        return ToolCall(
            call_id=call_id,
            name=name,
            arguments=arguments,
            raw=json.dumps(obj),
        )

    def format_result(self, result: ToolResult) -> bytes:
        """Format ToolResult as Codex-compatible JSON."""
        payload: dict[str, Any] = {
            "type": "function_call_output",
            "call_id": result.call_id,
            "output": result.output,
        }
        if result.error:
            payload["error"] = result.error
        return (json.dumps(payload) + "\n").encode("utf-8")

    def is_tool_call(self, line: bytes) -> bool:
        """Check if line looks like a Codex tool call."""
        try:
            obj = json.loads(line)
            return obj.get("type") in ("function_call", "tool_call")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False
