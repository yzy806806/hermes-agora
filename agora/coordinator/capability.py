"""Capability match scoring for agent-task assignment (Phase 9.3c).

Shared utility used by both the task assigner (9.2c) and
the agent protocol (9.3c) to score how well an agent's
capabilities match a task's requirements.
"""


def capability_match_score(
    agent_caps: list[str],
    required_caps: list[str],
) -> float:
    """Score how well agent capabilities match requirements.

    Returns 0.0 to 1.0:
    - Exact match of all required: 1.0
    - Partial match: len(intersection) / len(required)
    - Extra capabilities don't penalize
    - No requirements: 0.5 (neutral)
    """
    if not required_caps:
        return 0.5
    intersection = set(agent_caps) & set(required_caps)
    return len(intersection) / len(required_caps)