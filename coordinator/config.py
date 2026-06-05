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

    # Authentication
    require_api_key: bool = False
    api_key_header: str = "X-Agora-Key"

    model_config = {"env_prefix": "AGORA_"}


settings = Settings()
