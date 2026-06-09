"""Tests for task_gen module: heuristic, LLM, and validation."""

import json
import os
import pytest

from agora.coordinator.task_gen import generate_task_graph
from agora.coordinator.task_gen.validation import _validate_graph
from agora.coordinator.task_gen.heuristic import heuristic_generate
from agora.coordinator.task_models import TaskGraph, TaskNode


class MockStorage:
    async def get_messages(self, discussion_id):
        return [
            {"author": "alice", "content": "We should implement X"},
            {"author": "bob", "content": "Agreed, I'll handle the tests"},
        ]


@pytest.mark.asyncio
async def test_heuristic_generate_basic():
    """Heuristic creates one task per action_item, chained."""
    motion = {
        "id": "m-1",
        "action_items": json.dumps(["Implement X", "Add tests"]),
    }
    graph = heuristic_generate(motion)

    assert len(graph.tasks) == 2
    assert graph.tasks[0].title == "Implement X"
    assert graph.tasks[1].title == "Add tests"
    assert graph.tasks[0].depends_on == []
    assert graph.tasks[1].depends_on == [graph.tasks[0].id]


@pytest.mark.asyncio
async def test_heuristic_empty_action_items():
    """Heuristic handles empty action_items."""
    motion = {"id": "m-2", "action_items": "[]"}
    graph = heuristic_generate(motion)
    assert len(graph.tasks) == 0


@pytest.mark.asyncio
async def test_validate_graph_self_dependency():
    """Validation catches self-dependency."""
    task = TaskNode(
        id="t-1", graph_id="g-1", motion_id="m-1",
        title="Test", depends_on=["t-1"],
    )
    with pytest.raises(ValueError, match="depends on itself"):
        _validate_graph([task])


@pytest.mark.asyncio
async def test_validate_graph_unknown_dependency():
    """Validation catches unknown dependency."""
    task = TaskNode(
        id="t-1", graph_id="g-1", motion_id="m-1",
        title="Test", depends_on=["t-unknown"],
    )
    with pytest.raises(ValueError, match="unknown task"):
        _validate_graph([task])


@pytest.mark.asyncio
async def test_validate_graph_cycle():
    """Validation catches cycles."""
    t1 = TaskNode(id="t-1", graph_id="g-1", motion_id="m-1", title="A", depends_on=["t-2"])
    t2 = TaskNode(id="t-2", graph_id="g-1", motion_id="m-1", title="B", depends_on=["t-1"])
    with pytest.raises(ValueError, match="cycle"):
        _validate_graph([t1, t2])


@pytest.mark.asyncio
async def test_validate_graph_valid():
    """Validation passes for valid DAG."""
    t1 = TaskNode(id="t-1", graph_id="g-1", motion_id="m-1", title="A", depends_on=[])
    t2 = TaskNode(id="t-2", graph_id="g-1", motion_id="m-1", title="B", depends_on=["t-1"])
    _validate_graph([t1, t2])  # Should not raise


@pytest.mark.asyncio
async def test_generate_task_graph_llm_success():
    """LLM generation works with valid response."""
    async def mock_llm(prompt):
        return json.dumps([
            {"title": "Task A", "description": "Do A", "required_capabilities": ["code"], "depends_on": []},
            {"title": "Task B", "description": "Do B", "required_capabilities": ["test"], "depends_on": [0]},
        ])

    motion = {"id": "m-1", "discussion_id": "d-1", "title": "Test", "description": "", "decision": "", "rationale": "", "action_items": "[]"}
    graph = await generate_task_graph(motion, MockStorage(), mock_llm)

    assert len(graph.tasks) == 2
    assert graph.tasks[0].title == "Task A"
    assert graph.tasks[1].title == "Task B"
    assert graph.tasks[1].depends_on == [graph.tasks[0].id]


@pytest.mark.asyncio
async def test_generate_task_graph_llm_fallback():
    """Falls back to heuristic when LLM fails."""
    async def mock_llm(prompt):
        raise RuntimeError("LLM unavailable")

    motion = {"id": "m-1", "discussion_id": "d-1", "title": "Test", "action_items": json.dumps(["Item 1"])}
    graph = await generate_task_graph(motion, MockStorage(), mock_llm)

    assert len(graph.tasks) == 1
    assert graph.tasks[0].title == "Item 1"


@pytest.mark.asyncio
async def test_generate_task_graph_heuristic_mode():
    """Env override forces heuristic mode."""
    os.environ["AGORA_TASK_GEN_MODE"] = "heuristic"
    try:
        async def mock_llm(prompt):
            return json.dumps([{"title": "LLM Task"}])

        motion = {"id": "m-1", "action_items": json.dumps(["Heuristic Task"])}
        graph = await generate_task_graph(motion, MockStorage(), mock_llm)

        assert len(graph.tasks) == 1
        assert graph.tasks[0].title == "Heuristic Task"
    finally:
        del os.environ["AGORA_TASK_GEN_MODE"]
