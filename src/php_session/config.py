"""Configuration dataclass for session management.

Provides a configuration object to replace global settings access,
making the session manager more portable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import (
    DEFAULT_JSON_FIELDS,
    DEFAULT_LOCK_TIMEOUT,
    DEFAULT_SESSION_EXPIRE,
    LOCK_SUFFIX,
    SESSION_PREFIX,
)


@dataclass(frozen=True)
class SessionConfig:
    """Configuration for PHP session management.

    This dataclass replaces direct access to global settings,
    making the session manager more portable and testable.

    Attributes:
        session_expire: Session expiration time in seconds.
        lock_timeout: Lock acquisition timeout in seconds.
        session_prefix: Redis key prefix for session data.
        lock_suffix: Redis key suffix for lock keys.
        json_fields: Set of field names known to contain JSON.
        json_prefix: Prefix pattern for auto-detecting JSON fields.

    Example:
        >>> config = SessionConfig(
        ...     session_expire=3600,  # 1 hour
        ...     lock_timeout=10.0,
        ... )
        >>> manager = SessionManager(redis_client, config)
    """

    session_expire: int = DEFAULT_SESSION_EXPIRE
    lock_timeout: float = DEFAULT_LOCK_TIMEOUT
    session_prefix: str = SESSION_PREFIX
    lock_suffix: str = LOCK_SUFFIX
    json_fields: frozenset[str] = field(default_factory=lambda: DEFAULT_JSON_FIELDS)
    json_prefix: str | None = "trace_list_"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.session_expire <= 0:
            raise ValueError("session_expire must be positive")
        if self.lock_timeout <= 0:
            raise ValueError("lock_timeout must be positive")
        if not self.session_prefix:
            raise ValueError("session_prefix cannot be empty")
