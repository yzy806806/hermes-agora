"""OpenClaw adapter for CLI Bridge.

Parses OpenClaw custom output format and maps tool calls
to Agora format.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from .base import BaseCLIAdapter, ToolCall, ToolResult

logger = logging.getLogger(__name__)

# OpenClaw emits tool calls as: <<<TOOL:tool_name>>>json_args<<<END>>>
_TOOL_START = re.compile(r"<<<TOOL:(\w+)>>>")
_TOOL_END = re.compile(r"<<<END>>>")


class OpenClawAdapter(BaseCLIAdapter):
    """Adapter for OpenClaw CLI agent.

    OpenClaw uses a custom tagged format for tool calls:
    <<<TOOL:read_file>>>{"path":"/tmp/f.txt"}<<<END>>>
    """

    agent_type = "openclaw"

    def parse_output(self, raw: bytes) -> list[ToolCall]:
        """Parse OpenClaw tagged output into ToolCall list."""
        calls: list[ToolCall] = []
        text = raw.decode("utf-8", errors="replace")
        for match in _TOOL_START.finditer(text):
            name = match.group(1)
            rest = text[match.end():]
            end = _TOOL_END.search(rest)
            if not end:
                continue
            args_str = rest[: end.start()].strip()
            try:
                arguments = json.loads(args_str)
            except json.JSONDecodeError:
                arguments = {"raw": args_str}
            calls.append(ToolCall(
                call_id=uuid.uuid4().hex[:8],
                name=name,
                arguments=arguments,
                raw=match.group(0) + args_str + "<<<END>>>",
            ))
        return calls

    def format_result(self, result: ToolResult) -> bytes:
        """Format ToolResult in OpenClaw result format."""
        tag = "ERROR" if result.error else "RESULT"
        output = result.error if result.error else result.output
        payload = f"<<<{tag}:{result.name}>>>{output}<<<END>>>"
        return payload.encode("utf-8")

    def is_tool_call(self, line: bytes) -> bool:
        """Check if line contains an OpenClaw tool call tag."""
        return b"<<<TOOL:" in line


class PicoClawAdapter(BaseCLIAdapter):
    """Placeholder adapter for PicoClaw — TBD format."""

    agent_type = "picoclaw"

    def parse_output(self, raw: bytes) -> list[ToolCall]:
        """Not implemented yet — returns empty list."""
        logger.warning("PicoClaw adapter not yet implemented")
        return []

    def format_result(self, result: ToolResult) -> bytes:
        """Not implemented yet — returns empty bytes."""
        logger.warning("PicoClaw adapter not yet implemented")
        return b""

    def is_tool_call(self, line: bytes) -> bool:
        return False
