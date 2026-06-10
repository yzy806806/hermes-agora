"""Tests for plugin_extensions.py — Phase 10.3e extension point registries."""

import pytest

from agora.coordinator.plugin_extensions import (
    DiscussionPolicyRegistry,
    ExtensionRegistry,
    APIEndpointRegistry,
    TaskVerifierRegistry,
    VotingMethodRegistry,
    get_api_endpoint_registry,
    get_discussion_policy_registry,
    get_task_verifier_registry,
    get_voting_method_registry,
)


# -- Sample classes for testing registration --


class FakeVoteCounter:
    """Stub voting method for tests."""

    def count(self, votes: list[dict]) -> dict:
        return {"decision": "adopted"}


class FakeVerifier:
    """Stub task verifier for tests."""

    async def verify(self, task: dict) -> tuple[bool, str]:
        return True, "ok"


async def fake_webhook(request=None) -> dict:
    """Stub endpoint handler for tests."""
    return {"status": "ok"}


class FakePolicy:
    """Stub discussion policy for tests."""

    async def check(self, motion: dict) -> dict:
        return {"allowed": True}


# -- ExtensionRegistry base class tests --


class TestExtensionRegistry:
    """Test the base ExtensionRegistry via VotingMethodRegistry."""

    def setup_method(self):
        self.reg = VotingMethodRegistry()

    def test_register_and_get(self):
        self.reg.register("fake", FakeVoteCounter)
        assert self.reg.get("fake") is FakeVoteCounter

    def test_get_missing_returns_none(self):
        assert self.reg.get("nonexistent") is None

    def test_list_all_empty(self):
        assert self.reg.list_all() == []

    def test_list_all_returns_names(self):
        self.reg.register("a", FakeVoteCounter)
        self.reg.register("b", FakeVoteCounter)
        names = self.reg.list_all()
        assert set(names) == {"a", "b"}

    def test_has_registered(self):
        self.reg.register("x", FakeVoteCounter)
        assert self.reg.has("x") is True
        assert self.reg.has("y") is False

    def test_register_overwrites_with_warning(self, caplog):
        self.reg.register("dup", FakeVoteCounter)
        with caplog.at_level("WARNING"):
            self.reg.register("dup", FakeVoteCounter)
        assert "overwriting" in caplog.text
        assert self.reg.get("dup") is FakeVoteCounter


# -- VotingMethodRegistry tests --


class TestVotingMethodRegistry:

    def setup_method(self):
        self.reg = VotingMethodRegistry()

    def test_name(self):
        assert self.reg._name == "VotingMethodRegistry"

    def test_register_custom_voting(self):
        self.reg.register("quadratic", FakeVoteCounter)
        assert self.reg.get("quadratic") is FakeVoteCounter
        assert "quadratic" in self.reg.list_all()


# -- TaskVerifierRegistry tests --


class TestTaskVerifierRegistry:

    def setup_method(self):
        self.reg = TaskVerifierRegistry()

    def test_name(self):
        assert self.reg._name == "TaskVerifierRegistry"

    def test_register_verifier(self):
        self.reg.register("security_scan", FakeVerifier)
        assert self.reg.get("security_scan") is FakeVerifier


# -- APIEndpointRegistry tests --


class TestAPIEndpointRegistry:

    def setup_method(self):
        self.reg = APIEndpointRegistry()

    def test_name(self):
        assert self.reg._name == "APIEndpointRegistry"

    def test_register_endpoint(self):
        self.reg.register_endpoint(
            "webhook", "POST", "/api/v1/plugins/webhook", fake_webhook,
        )
        ep = self.reg.get_endpoint("webhook")
        assert ep is not None
        method, path, handler = ep
        assert method == "POST"
        assert path == "/api/v1/plugins/webhook"
        assert handler is fake_webhook

    def test_get_endpoint_missing(self):
        assert self.reg.get_endpoint("missing") is None

    def test_list_endpoints(self):
        self.reg.register_endpoint("a", "GET", "/a", fake_webhook)
        self.reg.register_endpoint("b", "POST", "/b", fake_webhook)
        eps = self.reg.list_endpoints()
        names = {e[0] for e in eps}
        assert names == {"a", "b"}

    def test_method_uppercased(self):
        self.reg.register_endpoint("x", "get", "/x", fake_webhook)
        ep = self.reg.get_endpoint("x")
        assert ep is not None
        method, _, _ = ep
        assert method == "GET"


# -- DiscussionPolicyRegistry tests --


class TestDiscussionPolicyRegistry:

    def setup_method(self):
        self.reg = DiscussionPolicyRegistry()

    def test_name(self):
        assert self.reg._name == "DiscussionPolicyRegistry"

    def test_register_policy(self):
        self.reg.register("time_limit", FakePolicy)
        assert self.reg.get("time_limit") is FakePolicy


# -- Global singleton accessor tests --


class TestGlobalSingletons:

    def test_voting_method_singleton(self):
        r1 = get_voting_method_registry()
        r2 = get_voting_method_registry()
        assert r1 is r2

    def test_task_verifier_singleton(self):
        assert get_task_verifier_registry() is get_task_verifier_registry()

    def test_api_endpoint_singleton(self):
        assert get_api_endpoint_registry() is get_api_endpoint_registry()

    def test_discussion_policy_singleton(self):
        assert get_discussion_policy_registry() is get_discussion_policy_registry()
