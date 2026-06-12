"""Tests for ToolAdapter, ToolCall, and ToolResult."""

import pytest

from agora_agent_sdk.tool_adapter import ToolAdapter, ToolCall, ToolResult


class TestToolCall:
    def test_default_values(self) -> None:
        tc = ToolCall(name="read_file")
        assert tc.name == "read_file"
        assert tc.arguments == {}
        assert tc.raw == ""

    def test_with_arguments(self) -> None:
        tc = ToolCall(
            name="read_file",
            arguments={"path": "/tmp/test.py"},
            raw="raw output",
        )
        assert tc.arguments["path"] == "/tmp/test.py"
        assert tc.raw == "raw output"


class TestToolResult:
    def test_success_result(self) -> None:
        result = ToolResult(output="file contents here")
        assert result.success is True
        assert result.error == ""

    def test_error_result(self) -> None:
        result = ToolResult(
            output="", success=False, error="File not found"
        )
        assert result.success is False
        assert result.error == "File not found"


class TestToolAdapter:
    def test_parse_tool_call_default(self) -> None:
        adapter = ToolAdapter()
        tc = adapter.parse_tool_call("unknown", "some raw text")
        assert tc.name == "unknown"
        assert tc.raw == "some raw text"

    def test_format_tool_result_success(self) -> None:
        adapter = ToolAdapter()
        result = ToolResult(output="42")
        formatted = adapter.format_tool_result("codex", result)
        assert formatted == "42"

    def test_format_tool_result_error(self) -> None:
        adapter = ToolAdapter()
        result = ToolResult(
            output="partial", success=False, error="timeout"
        )
        formatted = adapter.format_tool_result("codex", result)
        assert "ERROR: timeout" in formatted
        assert "partial" in formatted
