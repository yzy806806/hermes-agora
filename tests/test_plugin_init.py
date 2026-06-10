"""Tests for agora package init and CLI entry points."""

import subprocess
import sys

import pytest


class TestPackageInit:
    """Verify the agora package can be imported."""

    def test_import_agora(self):
        import agora
        assert agora.__version__ == "0.10.0"

    def test_import_coordinator(self):
        from agora.coordinator import __version__
        assert __version__ == "0.10.0"

    def test_import_agent_client(self):
        from agora.agent_client import AgoraClient, AgoraConfig
        assert AgoraClient is not None
        assert AgoraConfig is not None


class TestCLI:
    """Verify CLI entry points are accessible."""

    def test_cli_module_importable(self):
        from agora.cli import build_parser, main
        parser = build_parser()
        assert parser is not None

    def test_cli_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "agora", "--version"],
            capture_output=True, text=True,
        )
        assert "0.10.0" in result.stdout

    def test_cli_no_command_shows_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "agora"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
