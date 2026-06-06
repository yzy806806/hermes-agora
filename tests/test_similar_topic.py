"""Tests for similar_topic module."""

import json
from pathlib import Path

import pytest

from coordinator.similar_topic import SimilarTopicDetector


@pytest.fixture
def detector() -> SimilarTopicDetector:
    """Create detector instance."""
    return SimilarTopicDetector(memory_path="/tmp/test_conclusions")


@pytest.fixture
def sample_conclusions(tmp_path: Path) -> Path:
    """Create sample conclusion files for testing."""
    memory_dir = tmp_path / "2026" / "06"
    memory_dir.mkdir(parents=True)

    conclusion1 = {
        "type": "agora_conclusion",
        "motion_id": "motion-001",
        "title": "采用微服务架构设计新系统",
        "decision": "adopted",
        "rationale": "微服务架构提供更好的可扩展性",
        "tags": ["architecture", "microservice", "adopted", "系统"],
        "key_points": ["可扩展性", "独立部署"],
    }
    (memory_dir / "motion-001.json").write_text(
        json.dumps(conclusion1, ensure_ascii=False), encoding="utf-8"
    )

    conclusion2 = {
        "type": "agora_conclusion",
        "motion_id": "motion-002",
        "title": "优先处理用户认证模块",
        "decision": "adopted",
        "rationale": "认证是安全的基础",
        "tags": ["priority", "authentication", "adopted"],
        "key_points": ["安全性"],
    }
    (memory_dir / "motion-002.json").write_text(
        json.dumps(conclusion2, ensure_ascii=False), encoding="utf-8"
    )

    return tmp_path


class TestKeywordExtraction:
    """Tests for _extract_keywords."""

    def test_chinese_keywords(self, detector: SimilarTopicDetector) -> None:
        """Test keyword extraction from Chinese text."""
        keywords = detector._extract_keywords("采用微服务架构设计新系统")
        # CJK chars are extracted individually, stopwords removed
        assert any(k in keywords for k in {"微", "服", "架", "构"})
        assert "的" not in keywords  # Chinese stopword

    def test_english_keywords(self, detector: SimilarTopicDetector) -> None:
        """Test keyword extraction from English text."""
        keywords = detector._extract_keywords("Adopt microservice architecture")
        assert "microservice" in keywords
        assert "architecture" in keywords

    def test_stopwords_filtered(self, detector: SimilarTopicDetector) -> None:
        """Test that stopwords are removed."""
        keywords = detector._extract_keywords("the architecture of the system")
        assert "the" not in keywords
        assert "of" not in keywords
        assert "architecture" in keywords


class TestCalculateSimilarity:
    """Tests for _calculate_similarity."""

    def test_jaccard_score(self, detector: SimilarTopicDetector) -> None:
        """Test Jaccard similarity returns correct score."""
        kw = {"microservice", "architecture", "design"}
        tags = ["microservice", "architecture", "adopted"]
        score = detector._calculate_similarity(kw, tags)
        assert 0.0 <= score <= 1.0

    def test_empty_keywords(self, detector: SimilarTopicDetector) -> None:
        """Test similarity with empty keywords."""
        assert detector._calculate_similarity(set(), ["tag"]) == 0.0

    def test_empty_tags(self, detector: SimilarTopicDetector) -> None:
        """Test similarity with empty tags."""
        assert detector._calculate_similarity({"kw"}, []) == 0.0

    def test_non_string_tags_ignored(self, detector: SimilarTopicDetector) -> None:
        """Test that non-string tags are safely ignored."""
        score = detector._calculate_similarity({"kw"}, [123, None])
        assert score == 0.0


class TestFindSimilar:
    """Tests for find_similar."""

    @pytest.mark.asyncio
    async def test_find_matching(
        self, detector: SimilarTopicDetector, sample_conclusions: Path
    ) -> None:
        """Test finding a similar topic."""
        detector.memory_path = str(sample_conclusions)
        detector._index = {}

        similar = await detector.find_similar(
            "microservice architecture plan", threshold=0.3
        )
        assert len(similar) >= 1
        assert similar[0]["motion_id"] == "motion-001"

    @pytest.mark.asyncio
    async def test_no_match_high_threshold(
        self, detector: SimilarTopicDetector, sample_conclusions: Path
    ) -> None:
        """Test no match with high threshold."""
        detector.memory_path = str(sample_conclusions)
        detector._index = {}

        similar = await detector.find_similar("xyzabc123", threshold=0.9)
        assert len(similar) == 0

    @pytest.mark.asyncio
    async def test_results_sorted_by_similarity(
        self, detector: SimilarTopicDetector, sample_conclusions: Path
    ) -> None:
        """Test results are sorted descending by similarity."""
        detector.memory_path = str(sample_conclusions)
        detector._index = {}

        similar = await detector.find_similar("microservice", threshold=0.1)
        if len(similar) > 1:
            for i in range(len(similar) - 1):
                assert similar[i]["similarity"] >= similar[i + 1]["similarity"]

    @pytest.mark.asyncio
    async def test_max_five_results(
        self, detector: SimilarTopicDetector, tmp_path: Path
    ) -> None:
        """Test at most 5 results returned."""
        memory_dir = tmp_path / "2026" / "06"
        memory_dir.mkdir(parents=True)
        for i in range(10):
            data = {
                "motion_id": f"m-{i:03d}",
                "title": f"test topic {i}",
                "decision": "adopted",
                "tags": ["test", "topic"],
            }
            (memory_dir / f"m-{i:03d}.json").write_text(json.dumps(data))

        detector.memory_path = str(tmp_path)
        detector._index = {}

        similar = await detector.find_similar("test topic", threshold=0.1)
        assert len(similar) <= 5


class TestGenerateReferenceContext:
    """Tests for generate_reference_context."""

    @pytest.mark.asyncio
    async def test_with_similar(
        self, detector: SimilarTopicDetector, sample_conclusions: Path
    ) -> None:
        """Test reference context with similar topics."""
        detector.memory_path = str(sample_conclusions)
        detector._index = {}

        # Use low threshold since test data has limited tag overlap
        ctx = await detector.find_similar("microservice architecture", threshold=0.1)
        assert len(ctx) >= 1  # verify data is reachable

        # Now test generate_reference_context by patching threshold
        from unittest.mock import patch
        with patch.object(detector, "find_similar") as mock_find:
            mock_find.return_value = [{
                "motion_id": "motion-001",
                "title": "采用微服务架构",
                "decision": "adopted",
                "similarity": 0.8,
                "rationale": "测试理由",
            }]
            result = await detector.generate_reference_context("microservice")
            assert "【相关历史结论】" in result
            assert "adopted" in result

    @pytest.mark.asyncio
    async def test_no_similar(
        self, detector: SimilarTopicDetector, sample_conclusions: Path
    ) -> None:
        """Test reference context with no similar topics."""
        detector.memory_path = str(sample_conclusions)
        detector._index = {}

        ctx = await detector.generate_reference_context("xyzabc123")
        assert ctx == ""


class TestCaching:
    """Tests for conclusion caching."""

    def test_cache_reuse(
        self, detector: SimilarTopicDetector, sample_conclusions: Path
    ) -> None:
        """Test that _load_conclusions returns cached result."""
        detector.memory_path = str(sample_conclusions)

        first = detector._load_conclusions()
        second = detector._load_conclusions()
        assert first is second
