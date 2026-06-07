"""Tests for InputValidator and ValidationConfig."""
import pytest
from coordinator.input_validation import InputValidator, ValidationConfig


class TestInputValidator:
    def setup_method(self):
        self.validator = InputValidator()

    def test_sanitize_html_escapes(self):
        assert self.validator.sanitize_html("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"

    def test_sanitize_html_strips_script(self):
        result = self.validator.sanitize_html("<script>alert(1)</script>hi")
        assert "script" not in result.lower()
        assert "hi" in result

    def test_sanitize_html_strips_javascript_uri(self):
        result = self.validator.sanitize_html('javascript:alert(1)')
        assert "javascript" not in result.lower()

    def test_sanitize_html_strips_event_handlers(self):
        result = self.validator.sanitize_html('onclick=evil')
        assert "onclick" not in result.lower()

    def test_validate_agent_name_valid(self):
        assert self.validator.validate_agent_name("agent_01") == "agent_01"

    def test_validate_agent_name_invalid_chars(self):
        with pytest.raises(ValueError, match="Invalid agent name"):
            self.validator.validate_agent_name("bad-name!")

    def test_validate_agent_name_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            self.validator.validate_agent_name("a" * 65)

    def test_validate_speak_payload_ok(self):
        p = self.validator.validate_speak_payload({"content": "hello"})
        assert p["content"] == "hello"

    def test_validate_speak_payload_too_long(self):
        cfg = ValidationConfig(max_speak_length=10)
        v = InputValidator(cfg)
        with pytest.raises(ValueError, match="exceeds"):
            v.validate_speak_payload({"content": "a" * 11})

    def test_validate_speak_payload_sanitizes(self):
        p = self.validator.validate_speak_payload({"content": "<script>x</script>"})
        assert "script" not in p["content"].lower()

    def test_validate_motion_payload_ok(self):
        p = self.validator.validate_motion_payload({"title": "Vote"})
        assert p["title"] == "Vote"

    def test_validate_motion_payload_bad_title(self):
        with pytest.raises(ValueError, match="title"):
            self.validator.validate_motion_payload({"title": ""})

    def test_validate_vote_payload_valid(self):
        for choice in ("for", "against", "abstain"):
            p = self.validator.validate_vote_payload({"choice": choice})
            assert p["choice"] == choice

    def test_validate_vote_payload_invalid(self):
        with pytest.raises(ValueError, match="Invalid vote"):
            self.validator.validate_vote_payload({"choice": "maybe"})
