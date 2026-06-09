"""Task Generator module — LLM-based decomposition with heuristic fallback.

Public API: generate_task_graph(motion, storage, llm_call) -> TaskGraph
"""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from agora.coordinator.task_models import TaskGraph
from .generator import _llm_generate
from .heuristic import heuristic_generate
from .validation import _validate_graph

logger = logging.getLogger(__name__)


async def generate_task_graph(
    motion: dict,
    storage,  # Storage instance
    llm_call,  # Async callable: (prompt) -> str
) -> TaskGraph:
    """Generate a task graph from a closed discussion.

    Tries LLM first, falls back to heuristic on failure.
    Validates DAG integrity before returning.
    """
    mode = os.environ.get("AGORA_TASK_GEN_MODE", "llm")
    graph_id = str(uuid4())

    if mode == "heuristic":
        logger.info("Using heuristic mode (env override)")
        return heuristic_generate(motion)

    graph = await _llm_generate(motion, storage, llm_call, graph_id)

    if graph is None:
        logger.warning("LLM failed, falling back to heuristic")
        return heuristic_generate(motion)

    try:
        _validate_graph(graph.tasks)
        logger.info(f"Generated {len(graph.tasks)} tasks via LLM")
        return graph
    except ValueError as e:
        logger.warning(f"LLM graph invalid: {e}, falling back to heuristic")
        return heuristic_generate(motion)
