"""Pipeline discussion and decomposition phases (Phase 13)."""

from __future__ import annotations

import logging
from typing import Any

from agora.coordinator.pipeline_errors import (
    DiscussionFailedError, DecompositionFailedError,
)

logger = logging.getLogger(__name__)


async def create_and_run_discussion(
    bootstrap: Any, idea: str, project_id: str,
) -> str:
    """Phase: DISCUSSING — bootstrap a discussion and return motion_id.

    Raises:
        DiscussionFailedError: If discussion fails or no consensus.
    """
    try:
        from agora.coordinator.bootstrap.discussion_driver import (
            DiscussionConfig,
        )
        config = DiscussionConfig(
            motion_title=idea,
            motion_description=f"Auto-pipeline for: {idea}",
            participants=["architect", "developer", "reviewer"],
        )
        motion_id = await bootstrap.discussion_driver.start_dev_discussion(
            config,
        )
        result = await bootstrap.discussion_driver.wait_for_result(motion_id)
        if result.decision != "adopted":
            raise DiscussionFailedError(
                f"Discussion rejected: {result.decision}"
            )
        logger.info("Discussion adopted: motion=%s", motion_id)
        return motion_id
    except DiscussionFailedError:
        raise
    except Exception as exc:
        raise DiscussionFailedError(str(exc)) from exc


async def generate_task_graph(
    bootstrap: Any, motion_id: str,
) -> Any:
    """Phase: DECOMPOSING — generate a TaskGraph from discussion result.

    Raises:
        DecompositionFailedError: If task generation fails.
    """
    try:
        result = await bootstrap.discussion_driver.wait_for_result(motion_id)
        task_ids = await bootstrap.task_generator.from_discussion_result(
            result,
        )
        if not task_ids:
            raise DecompositionFailedError("No tasks generated")
        graph = _build_graph_from_tasks(motion_id, task_ids)
        logger.info("Generated graph with %d tasks", len(task_ids))
        return graph
    except DecompositionFailedError:
        raise
    except Exception as exc:
        raise DecompositionFailedError(str(exc)) from exc


def _build_graph_from_tasks(motion_id: str, task_ids: list[str]) -> dict:
    """Build a simple graph dict from generated task IDs."""
    return {
        "id": f"graph-{motion_id}",
        "motion_id": motion_id,
        "task_ids": task_ids,
    }
