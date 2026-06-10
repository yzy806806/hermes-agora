"""Configuration management for the Agora Coordinator service.

Priority: CLI args > env vars (AGORA_*) > config.yaml > defaults.
Supports ~/.agora/config.yaml for persistent configuration.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .config_loader import (
    ensure_agora_home,
    expand_path,
    load_default_config,
    load_yaml_config,
    merge_configs,
)


class YamlConfigSource(PydanticBaseSettingsSource):
    """Custom settings source that reads from config.yaml."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_data: dict[str, Any]):
        super().__init__(settings_cls)
        self._yaml_data = yaml_data

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        if field_name in self._yaml_data:
            return self._yaml_data[field_name], field_name, False
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._yaml_data


class Settings(BaseSettings):
    """Agora Coordinator settings.

    Priority: CLI args > env vars (AGORA_*) > config.yaml > built-in defaults.
    """

    # Service configuration
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = False

    # Database
    db_path: str = str(Path.home() / ".agora" / "data" / "agora.db")

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Discussion configuration
    default_rounds: int = 3
    default_voting_method: str = "simple_majority"
    speak_timeout_seconds: int = 120

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

    # Phase 9.3: Agent registration auth
    require_approval: bool = False        # env: AGORA_REQUIRE_APPROVAL
    admin_token: str = ""                 # env: AGORA_ADMIN_TOKEN

    # Heartbeat configuration
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 120
    heartbeat_max_missed: int = 3

    # Timeout configuration
    round_timeout_seconds: int = 300
    vote_timeout_seconds: int = 120
    discussion_timeout_seconds: int = 1800

    model_config = SettingsConfigDict(env_prefix="AGORA_")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: init (CLI) > env > yaml > defaults
        yaml_data = _get_yaml_data()
        yaml_source = YamlConfigSource(settings_cls, yaml_data)
        return init_settings, env_settings, yaml_source


def _get_yaml_data() -> dict[str, Any]:
    """Load and merge YAML config, expanding paths."""
    defaults = load_default_config()
    user_config = load_yaml_config()
    if user_config:
        defaults = merge_configs(defaults, user_config)
    for key in ("db_path",):
        if key in defaults and isinstance(defaults[key], str):
            defaults[key] = expand_path(defaults[key])
    return defaults


def load_settings(**cli_overrides: Any) -> Settings:
    """Create Settings with proper priority chain."""
    ensure_agora_home()
    return Settings(**cli_overrides)


settings = load_settings()
