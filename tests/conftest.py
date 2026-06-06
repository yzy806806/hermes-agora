"""Shared test fixtures for storage layer tests."""

import asyncio

import pytest
import pytest_asyncio

from coordinator.storage import Storage
from coordinator.judgment_tracker import JudgmentTracker


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    """Create a Storage instance with a temporary database."""
    db_path = str(tmp_path / "test_agora.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest_asyncio.fixture(loop_scope="session")
async def tracker(storage):
    """Create a JudgmentTracker instance using the test database."""
    return JudgmentTracker(storage.db_path)
