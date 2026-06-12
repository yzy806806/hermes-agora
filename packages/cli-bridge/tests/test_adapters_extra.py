"""Unit tests for Claude and OpenClaw adapters, and get_adapter factory."""
import json

import pytest

from agora_cli_bridge.adapters import (
    ClaudeAdapter,
    OpenClawAdapter,
    PicoClawAdapter,
    ToolResult,
    get_adapter,
)
from agora_cli_bridge.adapters.base import BaseCLIAdapter


class TestClaudeAdapter:
    """Tests for Claude Code (MCP) adapter."""

    def setup_method(self):
        self.adapter = ClaudeAdapter()

    def test_parse_tools_call(self):
        raw = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 42,
            "params": {
                "name": "read_file",
                "arguments": {"path": "/tmp/x.py"},
            },
        }).encode()
        calls = self.adapter.parse_output(raw)
        assert len(calls) == 1
        assert calls[0].call_id == "42"
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "/tmp/x.py"}

    def test_parse_input_key(self):
        """Claude MCP may use 'input' instead of 'arguments'."""
        raw = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {"name": "f", "input": {"k": "v"}},
        }).encode()
        calls = self.adapter.parse_output(raw)
        assert len(calls) == 1
        assert calls[0].arguments == {"k": "v"}

    def test_format_result(self):
        result = ToolResult(call_id="1", name="f", output="ok")
        out = self.adapter.format_result(result)
        obj = json.loads(out)
        assert obj["jsonrpc"] == "2.0"
        assert obj["id"] == "1"
        assert obj["result"]["content"][0]["text"] == "ok"

    def test_format_error_result(self):
        result = ToolResult(call_id="2", name="f", error="oops", success=False)
        out = self.adapter.format_result(result)
        obj = json.loads(out)
        assert "error" in obj
        assert obj["error"]["message"] == "oops"

    def test_is_tool_call(self):
        good = json.dumps({"jsonrpc": "2.0", "method": "tools/call"}).encode()
        assert self.adapter.is_tool_call(good)
        bad = json.dumps({"jsonrpc": "2.0", "method": "initialize"}).encode()
        assert not self.adapter.is_tool_call(bad)

    def test_ignore_non_rpc(self):
        assert self.adapter.parse_output(b"hello world") == []


class TestOpenClawAdapter:
    """Tests for OpenClaw adapter."""

    def setup_method(self):
        self.adapter = OpenClawAdapter()

    def test_parse_tool_tag(self):
        raw = b'<<<TOOL:read_file>>>{"path":"/tmp/a"}<<<END>>>'
        calls = self.adapter.parse_output(raw)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "/tmp/a"}

    def test_format_result(self):
        result = ToolResult(call_id="c1", name="f", output="data")
        out = self.adapter.format_result(result)
        assert b"<<<RESULT:f>>>data<<<END>>>" == out

    def test_format_error_result(self):
        result = ToolResult(call_id="c1", name="f", error="err", success=False)
        out = self.adapter.format_result(result)
        assert b"<<<ERROR:f>>>err<<<END>>>" == out

    def test_is_tool_call(self):
        assert self.adapter.is_tool_call(b"<<<TOOL:run>>>{}")
        assert not self.adapter.is_tool_call(b"plain text")


class TestPicoClawAdapter:
    """Tests for PicoClaw placeholder adapter."""

    def setup_method(self):
        self.adapter = PicoClawAdapter()

    def test_parse_returns_empty(self):
        assert self.adapter.parse_output(b"anything") == []

    def test_format_returns_empty(self):
        result = ToolResult(call_id="x", name="y", output="z")
        assert self.adapter.format_result(result) == b""


class TestGetAdapter:
    """Tests for the adapter factory."""

    def test_known_types(self):
        for t in ("codex", "claude", "openclaw", "picoclaw"):
            adapter = get_adapter(t)
            assert isinstance(adapter, BaseCLIAdapter)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_adapter("unknown_agent")
