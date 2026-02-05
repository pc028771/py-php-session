"""Tests for SessionConfig dataclass."""

from __future__ import annotations

import pytest

from php_session import SessionConfig
from php_session.constants import DEFAULT_JSON_FIELDS, DEFAULT_LOCK_TIMEOUT, DEFAULT_SESSION_EXPIRE


class TestSessionConfig:
    """Tests for SessionConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = SessionConfig()

        assert config.session_expire == DEFAULT_SESSION_EXPIRE
        assert config.lock_timeout == DEFAULT_LOCK_TIMEOUT
        assert config.session_prefix == "PHPREDIS_SESSION:"
        assert config.lock_suffix == "_LOCK"
        assert config.json_fields == DEFAULT_JSON_FIELDS
        assert config.json_prefix == "trace_list_"

    def test_custom_values(self) -> None:
        """Test that custom values can be set."""
        config = SessionConfig(
            session_expire=7200,
            lock_timeout=5.0,
            session_prefix="CUSTOM_SESSION:",
            lock_suffix="_CUSTOM_LOCK",
            json_fields=frozenset({"custom_field"}),
            json_prefix="custom_",
        )

        assert config.session_expire == 7200
        assert config.lock_timeout == 5.0
        assert config.session_prefix == "CUSTOM_SESSION:"
        assert config.lock_suffix == "_CUSTOM_LOCK"
        assert config.json_fields == frozenset({"custom_field"})
        assert config.json_prefix == "custom_"

    def test_invalid_session_expire(self) -> None:
        """Test that invalid session_expire raises ValueError."""
        with pytest.raises(ValueError, match="session_expire must be positive"):
            SessionConfig(session_expire=0)

        with pytest.raises(ValueError, match="session_expire must be positive"):
            SessionConfig(session_expire=-1)

    def test_invalid_lock_timeout(self) -> None:
        """Test that invalid lock_timeout raises ValueError."""
        with pytest.raises(ValueError, match="lock_timeout must be positive"):
            SessionConfig(lock_timeout=0)

        with pytest.raises(ValueError, match="lock_timeout must be positive"):
            SessionConfig(lock_timeout=-1.0)

    def test_invalid_session_prefix(self) -> None:
        """Test that empty session_prefix raises ValueError."""
        with pytest.raises(ValueError, match="session_prefix cannot be empty"):
            SessionConfig(session_prefix="")

    def test_config_is_frozen(self) -> None:
        """Test that config is immutable (frozen)."""
        config = SessionConfig()

        with pytest.raises(AttributeError):
            config.session_expire = 100  # type: ignore[misc]

    def test_none_json_prefix(self) -> None:
        """Test that json_prefix can be None to disable prefix matching."""
        config = SessionConfig(json_prefix=None)

        assert config.json_prefix is None
