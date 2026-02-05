"""Pure Python PHP session manager using Redis.

Compatible with PHP's redis session handler, allowing Python and PHP
to share sessions with proper distributed locking.

Basic usage:
    from php_session import SessionManager, SessionConfig
    from redis.asyncio import Redis

    redis = Redis.from_url("redis://localhost:6379")
    config = SessionConfig(session_expire=3600)
    manager = SessionManager(redis, config)

    # With explicit session_id
    async with manager.lock(session_id="abc123def456...") as session:
        session['cart_count'] = 5

With FastAPI/Starlette:
    from php_session import SessionManager, SessionConfig
    from php_session.contrib.starlette import PHPSessionMiddleware

    app = FastAPI()
    app.add_middleware(PHPSessionMiddleware)

    # Uses contextvars set by middleware
    async with manager.lock() as session:
        session['cart_count'] = 5
"""

from __future__ import annotations

from .config import SessionConfig
from .constants import (
    DEFAULT_JSON_FIELDS,
    DEFAULT_LOCK_TIMEOUT,
    DEFAULT_SESSION_EXPIRE,
    LOCK_RETRY_INTERVAL,
    LOCK_SUFFIX,
    PHPSESSID_PATTERN,
    RELEASE_LOCK_SCRIPT,
    SESSION_PREFIX,
)
from .context import get_current_session_id, set_current_session_id
from .decode import decode_json_fields
from .exceptions import (
    SessionContextError,
    SessionError,
    SessionLockError,
    SessionNotFoundError,
)
from .manager import SessionManager
from .sanitize import sanitize_phpsessid

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "SessionManager",
    "SessionConfig",
    # Exceptions
    "SessionError",
    "SessionLockError",
    "SessionNotFoundError",
    "SessionContextError",
    # Context helpers
    "set_current_session_id",
    "get_current_session_id",
    # Utility functions
    "sanitize_phpsessid",
    "decode_json_fields",
    # Constants
    "SESSION_PREFIX",
    "LOCK_SUFFIX",
    "DEFAULT_JSON_FIELDS",
    "DEFAULT_SESSION_EXPIRE",
    "DEFAULT_LOCK_TIMEOUT",
    "LOCK_RETRY_INTERVAL",
    "RELEASE_LOCK_SCRIPT",
    "PHPSESSID_PATTERN",
]
