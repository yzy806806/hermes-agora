"""LLM prompt templates for task decomposition."""

TASK_DECOMPOSITION_PROMPT = """\
You are a task decomposition engine. Given a closed discussion, generate
a task graph (DAG) for implementation.

Discussion Title: {title}
Description: {description}
Decision: {decision}
Rationale: {rationale}
Action Items: {action_items}

Discussion Transcript:
{transcript}

Output a JSON array of tasks. Each task has:
- "title": short human-readable name
- "description": detailed implementation spec
- "required_capabilities": array of capability strings from:
  [code, test, debug, refactor, review, security, docs, design, planning,
   research, deploy, release, monitor]
- "depends_on": array of task indices (0-based) that must complete first

Rules:
- Tasks should be granular (1 file or 1 concern per task)
- Dependencies should form a valid DAG (no cycles)
- Every task must have at least one capability
- Output ONLY the JSON array, no other text.

JSON:
"""
