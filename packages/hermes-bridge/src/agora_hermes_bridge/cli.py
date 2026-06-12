"""Hermes CLI utilities for the bridge."""

from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any

HERMES_CLI = "hermes"


def hermes_available() -> bool:
    """Check if hermes CLI is on PATH."""
    return shutil.which(HERMES_CLI) is not None


async def run_hermes(args: list[str]) -> dict[str, Any]:
    """Run a hermes CLI command and return parsed JSON output."""
    proc = await asyncio.create_subprocess_exec(
        HERMES_CLI, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip() or f"exit code {proc.returncode}"
        raise RuntimeError(f"hermes {' '.join(args)} failed: {err}")
    text = stdout.decode().strip()
    if not text:
        return {}
    return json.loads(text)
