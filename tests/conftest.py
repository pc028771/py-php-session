"""Test fixtures for py-php-session package."""

from __future__ import annotations

from typing import Any, Generator
from unittest.mock import AsyncMock

import pytest

from php_session import SessionConfig, SessionManager, set_current_session_id


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock Redis client for testing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=1)
    # Mock the register_script method to return a callable
    mock_script = AsyncMock(return_value=1)
    redis.register_script = lambda script: mock_script
    return redis


@pytest.fixture
def config() -> SessionConfig:
    """Create a default SessionConfig for testing."""
    return SessionConfig(
        session_expire=3600,
        lock_timeout=10.0,
    )


@pytest.fixture
def session_manager(mock_redis: AsyncMock, config: SessionConfig) -> SessionManager:
    """Create a SessionManager with mocked Redis."""
    return SessionManager(mock_redis, config)


@pytest.fixture(autouse=True)
def setup_session_context() -> Generator[None, None, None]:
    """Set up and clean up session context for each test."""
    # Use a valid 32-char session ID
    set_current_session_id("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
    yield
    set_current_session_id(None)
