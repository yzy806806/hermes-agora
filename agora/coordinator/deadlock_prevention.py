"""Circular dependency detection for agent discussions."""
from __future__ import annotations
import logging, uuid
from collections import defaultdict
from enum import Enum
from typing import Any
logger = logging.getLogger(__name__)

class DeadlockStatus(str, Enum):
    CLEAR = "clear"; WARNING = "warning"; DEADLOCK = "deadlock"

class ReferenceGraph:
    """Directed graph tracking agent references via dict storage."""
    def __init__(self) -> None:
        self._edges: dict[str, list[dict[str, Any]]] = defaultdict(list)
    def add_edge(self, from_node: str, to_node: str, metadata: dict | None = None) -> None:
        self._edges[from_node].append({"to": to_node, "meta": metadata or {}})
    def find_cycles(self, max_depth: int = 5) -> list[list[str]]:
        cycles: list[list[str]] = []
        for start in self._edges:
            self._dfs(start, start, [start], set(), cycles, max_depth)
        return cycles
    def _dfs(self, node: str, start: str, path: list[str], visited: set,
             cycles: list[list[str]], max_depth: int) -> None:
        if len(path) > max_depth: return
        for edge in self._edges.get(node, []):
            nxt = edge["to"]
            if nxt == start and len(path) >= 2: cycles.append(list(path))
            elif nxt not in visited:
                visited.add(nxt)
                self._dfs(nxt, start, path + [nxt], visited, cycles, max_depth)
                visited.discard(nxt)
    def get_recent_edges(self, agent_id: str, count: int = 5) -> list[dict]:
        return self._edges.get(agent_id, [])[-count:]

class DeadlockDetector:
    """Detects circular agent references that may cause discussion deadlock."""
    def __init__(self, window: int = 5) -> None:
        self._graph = ReferenceGraph()
        self._ref_count: dict[tuple[str, str], int] = defaultdict(int)
        self._window = window
    def track_reference(self, from_agent: str, to_agent: str, message_id: str) -> None:
        self._graph.add_edge(from_agent, to_agent, {"message_id": message_id})
        self._ref_count[(from_agent, to_agent)] += 1
        logger.debug("Reference: %s -> %s (msg %s)", from_agent, to_agent, message_id)
    def check_circular(self, agent_a: str, agent_b: str, window: int = 5) -> DeadlockStatus:
        total = self._ref_count.get((agent_a, agent_b), 0) + self._ref_count.get((agent_b, agent_a), 0)
        if total >= window * 2: return DeadlockStatus.DEADLOCK
        if total >= window: return DeadlockStatus.WARNING
        return DeadlockStatus.CLEAR
    def get_deadlock_risk(self) -> list[tuple[str, str, DeadlockStatus]]:
        agents = {a for a, _ in self._ref_count} | {b for _, b in self._ref_count}
        risks: list[tuple[str, str, DeadlockStatus]] = []
        seen: set[frozenset[str]] = set()
        for a in agents:
            for b in agents:
                if a >= b: continue
                pair = frozenset({a, b})
                if pair in seen: continue
                seen.add(pair)
                status = self.check_circular(a, b, self._window)
                if status != DeadlockStatus.CLEAR: risks.append((a, b, status))
        return risks
    def inject_break_signal(self, agent_a: str, agent_b: str) -> dict[str, Any]:
        logger.warning("BREAK signal for deadlock: %s <-> %s", agent_a, agent_b)
        return {"type": "BREAK", "agents": [agent_a, agent_b], "message_id": str(uuid.uuid4()),
                "reason": "Circular reference detected, redirecting discussion"}
