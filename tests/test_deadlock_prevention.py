"""Unit tests for coordinator/deadlock_prevention.py."""
import pytest
from coordinator.deadlock_prevention import DeadlockDetector, ReferenceGraph, DeadlockStatus


class TestDeadlockStatus:
    def test_values(self):
        assert DeadlockStatus.CLEAR == "clear"
        assert DeadlockStatus.WARNING == "warning"
        assert DeadlockStatus.DEADLOCK == "deadlock"


class TestReferenceGraph:
    def test_add_and_get_recent(self):
        g = ReferenceGraph()
        g.add_edge("A", "B", {"msg": "1"})
        g.add_edge("A", "C", {"msg": "2"})
        recent = g.get_recent_edges("A", count=1)
        assert len(recent) == 1 and recent[0]["to"] == "C"

    def test_no_cycle_linear(self):
        g = ReferenceGraph()
        g.add_edge("X", "Y"); g.add_edge("Y", "Z")
        assert g.find_cycles() == []

    def test_cycle_triangle(self):
        g = ReferenceGraph()
        g.add_edge("A", "B"); g.add_edge("B", "C"); g.add_edge("C", "A")
        cycles = g.find_cycles()
        assert len(cycles) >= 1

    def test_self_reference_is_cycle(self):
        g = ReferenceGraph()
        g.add_edge("A", "A")
        assert len(g.find_cycles()) > 0

    def test_max_depth_limits(self):
        g = ReferenceGraph()
        for i in range(10):
            g.add_edge(f"N{i}", f"N{i+1}")
        g.add_edge("N10", "N0")
        assert g.find_cycles(max_depth=5) == []
        assert len(g.find_cycles(max_depth=12)) > 0

    def test_get_recent_empty(self):
        g = ReferenceGraph()
        assert g.get_recent_edges("Z") == []


class TestDeadlockDetector:
    def test_clear_status(self):
        d = DeadlockDetector(window=3)
        d.track_reference("A", "B", "m1")
        assert d.check_circular("A", "B", window=3) == DeadlockStatus.CLEAR

    def test_warning_status(self):
        d = DeadlockDetector(window=3)
        d.track_reference("A", "B", "m1")
        d.track_reference("B", "A", "n1")
        d.track_reference("A", "B", "m2")
        assert d.check_circular("A", "B", window=3) == DeadlockStatus.WARNING

    def test_deadlock_status(self):
        d = DeadlockDetector(window=3)
        for i in range(3):
            d.track_reference("A", "B", f"m{i}")
            d.track_reference("B", "A", f"n{i}")
        assert d.check_circular("A", "B", window=3) == DeadlockStatus.DEADLOCK

    def test_get_deadlock_risk_empty(self):
        d = DeadlockDetector()
        assert d.get_deadlock_risk() == []

    def test_get_deadlock_risk_found(self):
        d = DeadlockDetector(window=2)
        for i in range(2):
            d.track_reference("A", "B", f"m{i}")
            d.track_reference("B", "A", f"n{i}")
        risks = d.get_deadlock_risk()
        assert len(risks) == 1
        assert risks[0][2] == DeadlockStatus.DEADLOCK

    def test_inject_break_signal(self):
        d = DeadlockDetector()
        msg = d.inject_break_signal("A", "B")
        assert msg["type"] == "BREAK"
        assert set(msg["agents"]) == {"A", "B"}
        assert "message_id" in msg
        assert "reason" in msg
