"""Bootstrap trigger types — data structures for the trigger system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TriggerType(str, Enum):
    """Supported bootstrap trigger types."""
    SCHEDULED = "scheduled"
    USER_REQUESTED = "user_requested"
    GITHUB_ISSUE = "github_issue"
    ROADMAP_CHANGE = "roadmap_change"


@dataclass
class TriggerEvent:
    """A bootstrap trigger event."""
    trigger_type: TriggerType
    topic: str
    source: str  # GitHub issue #, user_id, etc.
    context: str
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "trigger_type": self.trigger_type.value,
            "topic": self.topic,
            "source": self.source,
            "context": self.context,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
        }
