"""Tests for the plugin __init__.py — tool wrappers and register()."""

import asyncio
import importlib
import sys
import types

import pytest


def _load_plugin():
    """Load the root __init__.py as a module."""
    name = "hermes_agora_plugin"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, "/root/hermes-agora/__init__.py",
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class MockCtx:
    """Mock Hermes plugin context for testing register()."""

    def __init__(self):
        self.tools: dict = {}
        self.hooks: dict = {}
        self.config: dict = {}

    def register_tool(self, name: str, func) -> None:
        self.tools[name] = func

    def register_hook(self, name: str, func) -> None:
        self.hooks[name] = func


class TestRegister:
    def test_registers_all_tools(self):
        plugin = _load_plugin()
        ctx = MockCtx()
        plugin.register(ctx)
        expected = [
            "agora_create_motion", "agora_speak", "agora_vote",
            "agora_list_motions", "agora_get_history", "agora_get_result",
        ]
        for name in expected:
            assert name in ctx.tools, f"Missing tool: {name}"

    def test_registers_all_hooks(self):
        plugin = _load_plugin()
        ctx = MockCtx()
        plugin.register(ctx)
        expected = ["on_session_start", "on_session_end", "post_tool_call"]
        for name in expected:
            assert name in ctx.hooks, f"Missing hook: {name}"

    def test_tools_are_async(self):
        plugin = _load_plugin()
        ctx = MockCtx()
        plugin.register(ctx)
        for name, func in ctx.tools.items():
            assert asyncio.iscoroutinefunction(func), f"{name} is not async"

    def test_get_client_before_register_raises(self):
        plugin = _load_plugin()
        plugin._client = None
        with pytest.raises(RuntimeError, match="not registered"):
            asyncio.run(plugin.agora_create_motion(title="test"))
