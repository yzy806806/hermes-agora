"""Tests for BaseCLIAdapter ABC and ToolCall/ToolResult models."""
from __future__ import annotations

import pytest

from agora_cli_bridge.adapters.base import (
    BaseCLIAdapter,
    ToolCall,
    ToolResult,
)


class DummyAdapter(BaseCLIAdapter):
    """Minimal adapter for testing."""

    agent_type = "dummy"

    def parse_output(self, raw: bytes) -> list[ToolCall]:
        """Parse lines like: TOOL:name:{"arg": "val"}"""
        text = raw.decode("utf-8", errors="replace")
        if not text.startswith("TOOL:"):
            return []
        parts = text.split(":", 2)
        if len(parts) < 3:
            return []
        import json
        try:
            args = json.loads(parts[2])
        except json.JSONDecodeError:
            args = {}
        return [ToolCall(call_id="x", name=parts[1], arguments=args)]

    def format_result(self, result: ToolResult) -> bytes:
        return f"RESULT:{result.call_id}:{result.output}".encode()


def test_tool_call_dataclass() -> None:
    """ToolCall stores call_id, name, arguments, raw."""
    call = ToolCall(call_id="c1", name="read_file", arguments={"path": "/tmp/x"})
    assert call.call_id == "c1"
    assert call.name == "read_file"
    assert call.arguments == {"path": "/tmp/x"}


def test_tool_result_dataclass() -> None:
    """ToolResult stores call_id, name, output, error, success."""
    res = ToolResult(call_id="c1", name="read_file", output="file contents")
    assert res.call_id == "c1"
    assert res.output == "file contents"
    assert res.success is True


def test_adapter_parse_output() -> None:
    """DummyAdapter parses TOOL: lines correctly."""
    adapter = DummyAdapter()
    calls = adapter.parse_output(b'TOOL:read_file:{"path": "/tmp/x"}')
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments == {"path": "/tmp/x"}


def test_adapter_parse_non_tool_line() -> None:
    """Non-tool lines return empty list."""
    adapter = DummyAdapter()
    assert adapter.parse_output(b"just some text") == []


def test_adapter_format_result() -> None:
    """DummyAdapter formats results as RESULT: lines."""
    adapter = DummyAdapter()
    res = ToolResult(call_id="c1", name="f", output="ok")
    assert adapter.format_result(res) == b"RESULT:c1:ok"


def test_adapter_agent_type() -> None:
    """agent_type attribute identifies the adapter."""
    assert DummyAdapter().agent_type == "dummy"


def test_build_prompt_default() -> None:
    """Default build_prompt returns UTF-8 encoded task description."""
    adapter = DummyAdapter()
    prompt = adapter.build_prompt("do something")
    assert prompt == b"do something"


def test_is_tool_call_default() -> None:
    """Default is_tool_call returns False."""
    adapter = DummyAdapter()
    assert adapter.is_tool_call(b"anything") is False
