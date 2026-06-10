"""Tests for Phase 10.2b: TokenManager (JWT)."""
import pytest
from agora.coordinator.token_manager import TokenManager


@pytest.fixture
def tm() -> TokenManager:
    """TokenManager with a fixed secret for deterministic tests."""
    return TokenManager(secret="test-secret-key-at-least-32-characters!!")


class TestCreateToken:
    def test_create_returns_jwt_string(self, tm: TokenManager) -> None:
        token = tm.create_token("agent-1", "agent")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_with_tenant(self, tm: TokenManager) -> None:
        token = tm.create_token("agent-2", "admin", tenant_id="t1")
        payload = tm.validate_token(token)
        assert payload.tenant_id == "t1"

    def test_create_with_custom_expiry(self, tm: TokenManager) -> None:
        token = tm.create_token("agent-3", "agent", expires_delta=60)
        payload = tm.validate_token(token)
        assert payload.exp - payload.iat <= 61


class TestValidateToken:
    def test_valid_token(self, tm: TokenManager) -> None:
        token = tm.create_token("agent-1", "agent")
        payload = tm.validate_token(token)
        assert payload.agent_id == "agent-1"
        assert payload.role == "agent"

    def test_wrong_secret_raises(self) -> None:
        tm1 = TokenManager(secret="secret-a")
        tm2 = TokenManager(secret="secret-b")
        token = tm1.create_token("agent-1", "agent")
        with pytest.raises(ValueError, match="Invalid token"):
            tm2.validate_token(token)

    def test_expired_token_raises(self, tm: TokenManager) -> None:
        token = tm.create_token("agent-1", "agent", expires_delta=-1)
        with pytest.raises(ValueError, match="expired"):
            tm.validate_token(token)

    def test_malformed_token_raises(self, tm: TokenManager) -> None:
        with pytest.raises(ValueError):
            tm.validate_token("not.a.jwt")


class TestRevokeToken:
    def test_revoked_token_raises(self, tm: TokenManager) -> None:
        token = tm.create_token("agent-1", "agent")
        tm.revoke_token(token)
        with pytest.raises(ValueError, match="revoked"):
            tm.validate_token(token)

    def test_revoke_invalid_token_noop(self, tm: TokenManager) -> None:
        tm.revoke_token("garbage")  # should not raise


class TestRotateToken:
    def test_rotate_returns_new_token(self, tm: TokenManager) -> None:
        old = tm.create_token("agent-1", "admin", tenant_id="t1")
        new = tm.rotate_token(old)
        payload = tm.validate_token(new)
        assert payload.agent_id == "agent-1"
        assert payload.role == "admin"
        assert payload.tenant_id == "t1"

    def test_rotate_revokes_old(self, tm: TokenManager) -> None:
        old = tm.create_token("agent-1", "agent")
        tm.rotate_token(old)
        with pytest.raises(ValueError, match="revoked"):
            tm.validate_token(old)

    def test_rotate_invalid_raises(self, tm: TokenManager) -> None:
        with pytest.raises(ValueError, match="invalid"):
            tm.rotate_token("garbage.token.here")


class TestAutoSecret:
    def test_auto_generate_without_env(self) -> None:
        tm = TokenManager(secret="")
        token = tm.create_token("a", "agent")
        assert tm.validate_token(token).agent_id == "a"
