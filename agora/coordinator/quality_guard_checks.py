"""Quality guard check implementations — individual quality detectors."""

from __future__ import annotations

from .quality_guard_models import QualityAlert, QualityGuardConfig, QualityIssue


async def run_all_checks(
    messages: list[dict], config: QualityGuardConfig
) -> list[QualityAlert]:
    """Run all quality checks and aggregate alerts."""
    alerts: list[QualityAlert] = []
    alerts.extend(await check_argument_quality(messages, config))
    alerts.extend(await check_evidence_sparsity(messages, config))
    alerts.extend(await check_repetitive(messages, config))
    alerts.extend(await check_perspective_diversity(messages))
    alerts.extend(await check_rebuttal_strength(messages))
    return alerts


async def check_argument_quality(
    messages: list[dict], config: QualityGuardConfig
) -> list[QualityAlert]:
    """Check for low-quality arguments (short or trivial content)."""
    alerts = []
    for msg in messages:
        content = msg.get("content", "")
        agent_id = msg.get("agent_id", "unknown")
        if len(content) < config.min_content_length or _is_trivial(content, config):
            alerts.append(QualityAlert(
                issue=QualityIssue.LOW_ARGUMENT_QUALITY,
                severity=0.7,
                details=f"Agent {agent_id} 发言缺乏实质内容",
                affected_agents=[agent_id],
            ))
    return alerts


async def check_evidence_sparsity(
    messages: list[dict], config: QualityGuardConfig
) -> list[QualityAlert]:
    """Check if messages lack evidence support."""
    no_evidence = [m for m in messages if not m.get("evidence")]
    ratio = len(no_evidence) / max(len(messages), 1)
    if ratio > config.evidence_sparse_threshold:
        return [QualityAlert(
            issue=QualityIssue.EVIDENCE_SPARSE,
            severity=0.8,
            details=f"{int(ratio * 100)}%+ 发言缺乏证据支持",
            affected_agents=[m.get("agent_id", "unknown") for m in no_evidence],
        )]
    return []


async def check_repetitive(
    messages: list[dict], config: QualityGuardConfig
) -> list[QualityAlert]:
    """Detect repetitive arguments by comparing content prefixes."""
    content_hashes: dict[int, int] = {}
    for msg in messages:
        h = hash(msg.get("content", "")[:100])
        content_hashes[h] = content_hashes.get(h, 0) + 1

    # Count messages that are duplicates (appear more than once)
    duplicate_count = sum(c for h, c in content_hashes.items() if c > 1)
    if duplicate_count > len(messages) * config.repetitive_threshold:
        return [QualityAlert(
            issue=QualityIssue.REPETITIVE_ARGUMENTS,
            severity=0.6,
            details="超过30%的发言内容重复",
            affected_agents=[],
        )]
    return []


async def check_perspective_diversity(messages: list[dict]) -> list[QualityAlert]:
    """Check if discussion has diverse perspectives."""
    stances = {m.get("stance") for m in messages if m.get("stance")}
    if len(stances) < 2:
        return [QualityAlert(
            issue=QualityIssue.SINGLE_PERSPECTIVE,
            severity=0.9,
            details="讨论仅有一个立场",
            affected_agents=[],
        )]
    return []


async def check_rebuttal_strength(messages: list[dict]) -> list[QualityAlert]:
    """Check if there are meaningful rebuttals (replies to others)."""
    has_reply = sum(1 for m in messages if m.get("reply_to"))
    if len(messages) >= 4 and has_reply == 0:
        return [QualityAlert(
            issue=QualityIssue.WEAK_REBUTTAL,
            severity=0.5,
            details="讨论缺乏反驳和互动",
            affected_agents=[],
        )]
    return []


def _is_trivial(content: str, config: QualityGuardConfig) -> bool:
    """Check if content is trivial (just bare agreement/disagreement)."""
    stripped = content.strip()
    return any(stripped == p for p in config.trivial_phrases)
