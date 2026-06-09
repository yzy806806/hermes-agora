"""Input validation for Hermes Agora."""
import html
import re
from dataclasses import dataclass


@dataclass
class ValidationConfig:
    """Configuration for input validation and rate limits."""
    max_speak_length: int = 5000
    max_motion_title: int = 200
    rate_limit_speak: int = 10  # per minute
    rate_limit_vote: int = 5   # per minute


class InputValidator:
    """Validates and sanitizes agent inputs."""

    def __init__(self, config: ValidationConfig | None = None):
        self.config = config or ValidationConfig()

    def sanitize_html(self, text: str) -> str:
        """Strip dangerous HTML/JS from text."""
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.I | re.S)
        text = re.sub(r'javascript:', '', text, flags=re.I)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.I)
        return html.escape(text)

    def validate_agent_name(self, name: str) -> str:
        """Validate agent name: alphanumeric + underscore only."""
        if not re.match(r'^[A-Za-z0-9_]+$', name):
            raise ValueError(f"Invalid agent name: {name!r}")
        if len(name) > 64:
            raise ValueError("Agent name too long (max 64)")
        return name

    def validate_speak_payload(self, payload: dict) -> dict:
        """Validate speak content (max length, no XSS)."""
        content = payload.get("content", "")
        if len(content) > self.config.max_speak_length:
            raise ValueError(f"Speak content exceeds {self.config.max_speak_length} chars")
        payload["content"] = self.sanitize_html(content)
        return payload

    def validate_motion_payload(self, payload: dict) -> dict:
        """Validate motion creation data."""
        title = payload.get("title", "")
        if not title or len(title) > self.config.max_motion_title:
            raise ValueError(f"Motion title must be 1-{self.config.max_motion_title} chars")
        payload["title"] = self.sanitize_html(title)
        if "description" in payload:
            payload["description"] = self.sanitize_html(payload["description"])
        return payload

    def validate_vote_payload(self, payload: dict) -> dict:
        """Validate vote data."""
        choice = payload.get("choice")
        if choice not in ("for", "against", "abstain"):
            raise ValueError(f"Invalid vote choice: {choice!r}")
        return payload
