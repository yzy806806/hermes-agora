"""Shared test fixtures for storage layer tests."""

import asyncio

import pytest
import pytest_asyncio

from coordinator.storage import Storage


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
