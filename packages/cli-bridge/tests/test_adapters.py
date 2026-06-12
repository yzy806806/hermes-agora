"""Unit tests for CLI Bridge adapters."""
import json

import pytest

from agora_cli_bridge.adapters import (
    CodexAdapter,
    ClaudeAdapter,
    OpenClawAdapter,
    PicoClawAdapter,
    ToolCall,
    ToolResult,
    get_adapter,
)


class TestCodexAdapter:
    """Tests for Codex (OpenAI) adapter."""

    def setup_method(self):
        self.adapter = CodexAdapter()

    def test_parse_function_call(self):
        raw = json.dumps({
            "type": "function_call",
            "id": "call_123",
            "name": "read_file",
            "arguments": {"path": "/tmp/f.txt"},
        }).encode()
        calls = self.adapter.parse_output(raw)
        assert len(calls) == 1
        assert calls[0].call_id == "call_123"
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "/tmp/f.txt"}

    def test_parse_string_arguments(self):
        raw = json.dumps({
            "type": "function_call",
            "id": "call_456",
            "name": "run_cmd",
            "arguments": '{"cmd": "ls"}',
        }).encode()
        calls = self.adapter.parse_output(raw)
        assert len(calls) == 1
        assert calls[0].arguments == {"cmd": "ls"}

    def test_parse_multiple_lines(self):
        line1 = json.dumps({"type": "function_call", "id": "a", "name": "f1", "arguments": {}})
        line2 = json.dumps({"type": "text", "content": "hello"})
        line3 = json.dumps({"type": "tool_call", "id": "b", "name": "f2", "arguments": {}})
        raw = f"{line1}\n{line2}\n{line3}".encode()
        calls = self.adapter.parse_output(raw)
        assert len(calls) == 2

    def test_format_result(self):
        result = ToolResult(call_id="c1", name="read_file", output="file content")
        out = self.adapter.format_result(result)
        obj = json.loads(out)
        assert obj["type"] == "function_call_output"
        assert obj["call_id"] == "c1"
        assert obj["output"] == "file content"

    def test_format_result_with_error(self):
        result = ToolResult(call_id="c2", name="x", error="failed", success=False)
        out = self.adapter.format_result(result)
        obj = json.loads(out)
        assert obj["error"] == "failed"

    def test_is_tool_call(self):
        assert self.adapter.is_tool_call(json.dumps({"type": "function_call", "id": "x", "name": "f", "arguments": {}}).encode())
        assert not self.adapter.is_tool_call(b"plain text")

    def test_empty_input(self):
        assert self.adapter.parse_output(b"") == []
