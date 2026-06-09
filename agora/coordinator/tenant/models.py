"""Tenant and TenantConfig data models for multi-tenancy (Phase 8.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TenantConfig:
    """Per-tenant configuration and resource limits."""

    max_agents: int = 10
    max_concurrent_discussions: int = 3
    default_voting_method: str = "simple_majority"
    allow_custom_voting_methods: bool = True
    quality_threshold: float = 0.6
    discussion_timeout_seconds: int = 3600
    auto_close_inactive_seconds: int = 86400

    def to_dict(self) -> dict:
        return {
            "max_agents": self.max_agents,
            "max_concurrent_discussions": self.max_concurrent_discussions,
            "default_voting_method": self.default_voting_method,
            "allow_custom_voting_methods": self.allow_custom_voting_methods,
            "quality_threshold": self.quality_threshold,
            "discussion_timeout_seconds": self.discussion_timeout_seconds,
            "auto_close_inactive_seconds": self.auto_close_inactive_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TenantConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Tenant:
    """A single tenant (isolated discussion space)."""

    tenant_id: str
    name: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    config: TenantConfig = field(default_factory=TenantConfig)

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "config": self.config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Tenant:
        cfg = data.get("config", {})
        return cls(
            tenant_id=data["tenant_id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            config=TenantConfig.from_dict(cfg) if isinstance(cfg, dict) else TenantConfig(),
        )
