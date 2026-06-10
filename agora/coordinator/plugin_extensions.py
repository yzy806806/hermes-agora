"""Plugin Extension Points — registries for custom plugin contributions.

Phase 10.3e: Provides typed registries for plugins to register:
- Custom voting methods
- Custom task verifiers
- Custom REST API endpoints
- Custom discussion policies

Each registry follows the same pattern: register(name, cls), get(name), list_all().
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExtensionRegistry(ABC):
    """Base class for all plugin extension registries.

    Provides common registration, lookup, and listing operations.
    Subclasses define the type of extension they manage.
    """

    def __init__(self, name: str):
        self._name = name
        self._registry: dict[str, type] = {}

    def register(self, name: str, cls: type) -> None:
        """Register an extension class under a unique name."""
        if name in self._registry:
            logger.warning(
                "%s: overwriting existing registration for '%s'",
                self._name, name,
            )
        self._registry[name] = cls
        logger.info("%s: registered '%s'", self._name, name)

    def get(self, name: str) -> type | None:
        """Look up an extension class by name. Returns None if not found."""
        return self._registry.get(name)

    def list_all(self) -> list[str]:
        """Return all registered extension names."""
        return list(self._registry.keys())

    def has(self, name: str) -> bool:
        """Check if an extension is registered."""
        return name in self._registry


class VotingMethodRegistry(ExtensionRegistry):
    """Registry for custom voting method implementations.

    Plugins can register custom vote counters that implement
    the VoteCounter protocol (see voting/factory.py).

    Example:
        class QuadraticVotingCounter:
            def count(self, votes: list[dict]) -> dict:
                ...

        registry.register("quadratic_voting", QuadraticVotingCounter)
    """

    def __init__(self):
        super().__init__("VotingMethodRegistry")


class TaskVerifierRegistry(ExtensionRegistry):
    """Registry for custom task verification strategies.

    Plugins can register custom verifiers that check task results
    beyond the built-in auto-checks (file existence, etc.).

    Example:
        class SecurityScanVerifier:
            async def verify(self, task: dict) -> tuple[bool, str]:
                # Run bandit/semgrep on changed files
                ...

        registry.register("security_scan", SecurityScanVerifier)
    """

    def __init__(self):
        super().__init__("TaskVerifierRegistry")


class APIEndpointRegistry(ExtensionRegistry):
    """Registry for custom REST API endpoints from plugins.

    Plugins can register FastAPI route handlers that will be
    mounted under /api/v1/plugins/{name}/.

    Example:
        async def handle_webhook(request: Request) -> JSONResponse:
            ...

        registry.register("webhook", handle_webhook)
    """

    def __init__(self):
        super().__init__("APIEndpointRegistry")
        # Store (method, path, handler) tuples for endpoints
        self._endpoints: dict[str, tuple[str, str, Callable]] = {}

    def register_endpoint(
        self, name: str, method: str, path: str, handler: Callable,
    ) -> None:
        """Register a REST endpoint with HTTP method and path."""
        self._endpoints[name] = (method.upper(), path, handler)
        logger.info(
            "APIEndpointRegistry: registered %s %s -> %s",
            method.upper(), path, name,
        )

    def get_endpoint(self, name: str) -> tuple[str, str, Callable] | None:
        """Get endpoint tuple (method, path, handler) by name."""
        return self._endpoints.get(name)

    def list_endpoints(self) -> list[tuple[str, str, str]]:
        """Return list of (name, method, path) for all endpoints."""
        return [
            (name, method, path)
            for name, (method, path, _) in self._endpoints.items()
        ]


class DiscussionPolicyRegistry(ExtensionRegistry):
    """Registry for custom discussion policies.

    Plugins can register policy checkers that enforce custom rules
    during discussions (time limits, participant caps, etc.).

    Example:
        class TimeLimitPolicy:
            async def check(self, motion: dict) -> dict:
                # Return {"allowed": False, "reason": "..."} if violated
                ...

        registry.register("time_limit", TimeLimitPolicy)
    """

    def __init__(self):
        super().__init__("DiscussionPolicyRegistry")


# Global singleton instances
_voting_method_registry = VotingMethodRegistry()
_task_verifier_registry = TaskVerifierRegistry()
_api_endpoint_registry = APIEndpointRegistry()
_discussion_policy_registry = DiscussionPolicyRegistry()


def get_voting_method_registry() -> VotingMethodRegistry:
    """Get the global voting method registry."""
    return _voting_method_registry


def get_task_verifier_registry() -> TaskVerifierRegistry:
    """Get the global task verifier registry."""
    return _task_verifier_registry


def get_api_endpoint_registry() -> APIEndpointRegistry:
    """Get the global API endpoint registry."""
    return _api_endpoint_registry


def get_discussion_policy_registry() -> DiscussionPolicyRegistry:
    """Get the global discussion policy registry."""
    return _discussion_policy_registry
