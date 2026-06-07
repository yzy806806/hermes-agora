"""Configuration management for the Agora Coordinator service."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Agora Coordinator settings, loaded from environment variables with AGORA_ prefix."""

    # Service configuration
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = False

    # Database
    db_path: str = "data/agora.db"

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Discussion configuration
    default_rounds: int = 3
    default_voting_method: str = "simple_majority"
    speak_timeout_seconds: int = 120
    vote_timeout_seconds: int = 60

    # Smart discussion configuration
    smart_discussion_enabled: bool = True
    devils_advocate_enabled: bool = True
    max_rounds: int = 5
    min_messages_for_early_vote: int = 6

    # Realtime evaluation
    realtime_eval_enabled: bool = True
    realtime_consensus_threshold: float = 0.8
    realtime_min_messages: int = 3

    # Consensus jump
    consensus_jump_enabled: bool = True
    consensus_jump_ratio: float = 0.7

    # Dynamic rounds
    dynamic_rounds_enabled: bool = True
    dynamic_min_rounds: int = 2
    dynamic_max_rounds: int = 5
    dynamic_adaptive: bool = True
    dynamic_quality_threshold: float = 0.7
    dynamic_low_quality_threshold: float = 0.4

    # Assessment thresholds
    consensus_threshold_high: float = 0.7
    consensus_threshold_moderate: float = 0.5

    # Authentication
    require_api_key: bool = False
    api_key_header: str = "X-Agora-Key"

    # Heartbeat configuration
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 10
    heartbeat_max_missed: int = 3

    # Timeout configuration
    round_timeout_seconds: int = 300
    vote_timeout_seconds: int = 120
    discussion_timeout_seconds: int = 1800

    model_config = {"env_prefix": "AGORA_"}


settings = Settings()
