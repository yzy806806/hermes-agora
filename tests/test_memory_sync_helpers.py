"""Tests for MemorySync helper methods."""

from agora.coordinator.conclusion_types import DiscussionConclusion
from agora.coordinator.memory_sync import MemorySync


class TestExtractKeyPoints:
    def test_filters_short_messages(self):
        msgs = [
            {"content": "short"},
            {"content": "x" * 60},
            {"content": "y" * 80},
        ]
        pts = MemorySync._extract_key_points(msgs)
        assert len(pts) == 2
        assert pts[0].startswith("y")  # longest first

    def test_limit(self):
        msgs = [{"content": "z" * 60, "agent_id": f"a{i}"} for i in range(10)]
        assert len(MemorySync._extract_key_points(msgs)) == 5

    def test_empty(self):
        assert MemorySync._extract_key_points([]) == []


class TestSummarizeVotes:
    def test_basic(self):
        votes = [
            {"vote": "yes"}, {"vote": "yes"}, {"vote": "no"},
        ]
        assert MemorySync._summarize_votes(votes) == {"yes": 2, "no": 1}

    def test_empty(self):
        assert MemorySync._summarize_votes([]) == {}


class TestGenerateTags:
    def test_includes_decision_and_method(self):
        c = DiscussionConclusion(
            motion_id="m1", title="Test topic", decision="adopted",
            voting_method="ranked_choice",
        )
        tags = MemorySync._generate_tags(c)
        assert "adopted" in tags
        assert "ranked_choice" in tags

    def test_extracts_title_keywords(self):
        c = DiscussionConclusion(
            motion_id="m1", title="Adopt microservice architecture",
            decision="adopted",
        )
        tags = MemorySync._generate_tags(c)
        assert "adopt" in tags
        assert "microservice" in tags
        assert "architecture" in tags

    def test_filters_stopwords(self):
        c = DiscussionConclusion(
            motion_id="m1", title="Is the best for the team",
            decision="adopted",
        )
        tags = MemorySync._generate_tags(c)
        assert "the" not in tags
        assert "is" not in tags
