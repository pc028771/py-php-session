"""PHP Session Manager using Redis - compatible with PHP redis extension.

This module provides a Redis-based session manager that is fully compatible with
PHP's redis session handler, allowing Python and PHP to share sessions with
proper distributed locking.

Reference: PHP redis session handler uses the same lock key format and mechanism.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import phpserialize
from redis.asyncio import Redis

from .config import SessionConfig
from .constants import LOCK_RETRY_INTERVAL, RELEASE_LOCK_SCRIPT
from .context import get_current_session_id
from .decode import decode_json_fields
from .exceptions import SessionContextError, SessionLockError


class SessionManager:
    """Async Redis-based PHP session manager.

    Similar to PHP session.save_handler with Redis. Provides PHP-compatible
    distributed locking so Python and PHP can safely share sessions.

    Usage:
        # Initialize with Redis client and config
        config = SessionConfig(session_expire=3600, lock_timeout=10.0)
        manager = SessionManager(redis_client, config)

        # With lock (recommended - auto load/save like PHP)
        async with manager.lock(session_id="abc123") as session:
            session['cart_count'] = 5
            # auto-saved when exiting

        # Or use contextvars (set by middleware)
        async with manager.lock() as session:
            session['cart_count'] = 5

        # Read-only (no lock needed)
        cart = await manager.get('scart_items', session_id="abc123")
    """

    def __init__(
        self,
        redis: Redis[bytes],
        config: SessionConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the session manager.

        Args:
            redis: Async Redis client instance.
            config: Session configuration. Uses defaults if None.
            logger: Optional logger for debugging.
        """
        self._redis = redis
        self._config = config or SessionConfig()
        self._logger = logger
        self._release_lock_script = self._redis.register_script(RELEASE_LOCK_SCRIPT)

    def _resolve_session_id(self, session_id: str | None) -> str:
        """Resolve session_id from parameter or contextvars.

        Args:
            session_id: Explicit session ID, or None to use contextvars.

        Returns:
            The resolved session ID.

        Raises:
            SessionContextError: If no session_id available.
        """
        if session_id is not None:
            return session_id

        ctx_session_id = get_current_session_id()
        if ctx_session_id is None:
            raise SessionContextError()
        return ctx_session_id

    def _session_key(self, session_id: str) -> str:
        """Build Redis key for session data."""
        return f"{self._config.session_prefix}{session_id}"

    def _lock_key(self, session_id: str) -> str:
        """Build Redis key for session lock (PHP compatible format)."""
        return f"{self._session_key(session_id)}{self._config.lock_suffix}"

    def _decode_session(self, raw: bytes) -> dict[str, Any]:
        """Decode raw PHP-serialized session data."""
        data: dict[str, Any] = phpserialize.loads(
            raw,
            decode_strings=True,
            object_hook=lambda _name, d: dict(d),
        )
        return decode_json_fields(
            data,
            json_fields=self._config.json_fields,
            json_prefix=self._config.json_prefix,
        )

    @asynccontextmanager
    async def lock(
        self,
        session_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """PHP redis session compatible lock - auto load/save.

        PHP Compatibility:
            - Lock key: {SESSION_PREFIX}{session_id}_LOCK (same as PHP)
            - Lock acquire: SET key token NX PX expiry_ms (same as PHP)
            - Lock release: Lua script checking token (same as PHP)
            - Python waits for PHP's lock, PHP waits for Python's lock

        Args:
            session_id: Explicit session ID, or None to use contextvars.

        Yields:
            Session data dict that can be modified directly.

        Raises:
            SessionLockError: If lock cannot be acquired within timeout.
            SessionContextError: If no session_id available.

        Example:
            async with session_manager.lock(session_id="abc123") as session:
                session['cart_count'] = 5
                # auto-saved when exiting
        """
        resolved_id = self._resolve_session_id(session_id)
        lock_key = self._lock_key(resolved_id)
        token = secrets.token_hex(16)
        acquired = False

        # Acquire lock (matching PHP's SET NX PX pattern)
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < self._config.lock_timeout:
            result = await self._redis.set(
                lock_key,
                token,
                nx=True,
                px=int(self._config.lock_timeout * 1000),
            )
            if result:
                acquired = True
                break
            await asyncio.sleep(LOCK_RETRY_INTERVAL)

        if not acquired:
            raise SessionLockError(resolved_id, self._config.lock_timeout)

        if self._logger:
            self._logger.debug(
                "Session lock acquired: %s", resolved_id[:8] + "..."
            )

        # Load session data
        raw = await self._redis.get(self._session_key(resolved_id))
        session_data: dict[str, Any] = {}
        if raw:
            session_data = self._decode_session(raw)

        try:
            yield session_data  # User can modify this dict directly
        finally:
            # Auto-save session data
            await self._redis.set(
                self._session_key(resolved_id),
                phpserialize.dumps(session_data),
                ex=self._config.session_expire,
            )
            # Release lock using Lua script (same as PHP)
            await self._release_lock_script(keys=[lock_key], args=[token])
            if self._logger:
                self._logger.debug(
                    "Session saved and lock released: %s", resolved_id[:8] + "..."
                )

    async def get(
        self,
        key: str | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Get session data or specific key (read-only, no lock).

        Args:
            key: If provided, return session[key]. Otherwise return entire session.
            session_id: Explicit session ID, or None to use contextvars.

        Returns:
            Session data dict, specific key value, or None if not found.

        Raises:
            SessionContextError: If no session_id available.
        """
        resolved_id = self._resolve_session_id(session_id)
        raw = await self._redis.get(self._session_key(resolved_id))
        if raw is None:
            return None

        data = self._decode_session(raw)

        if key is None:
            return data
        return data.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        session_id: str | None = None,
    ) -> None:
        """Set a session key (use lock() for safety in concurrent scenarios).

        Args:
            key: Session key to set.
            value: Value to store.
            session_id: Explicit session ID, or None to use contextvars.

        Raises:
            SessionContextError: If no session_id available.
        """
        resolved_id = self._resolve_session_id(session_id)

        # Read current session
        raw = await self._redis.get(self._session_key(resolved_id))
        data: dict[str, Any] = {}
        if raw:
            data = phpserialize.loads(
                raw,
                decode_strings=True,
                object_hook=lambda _name, d: dict(d),
            )

        # Update key
        data[key] = value

        # Write back
        await self._redis.set(
            self._session_key(resolved_id),
            phpserialize.dumps(data),
            ex=self._config.session_expire,
        )
        if self._logger:
            self._logger.info(
                "Session key set: %s, key=%s", resolved_id[:8] + "...", key
            )

    async def save(
        self,
        data: dict[str, Any],
        session_id: str | None = None,
    ) -> None:
        """Save entire session data (use lock() for safety).

        Args:
            data: Complete session data dict to save.
            session_id: Explicit session ID, or None to use contextvars.

        Raises:
            SessionContextError: If no session_id available.
        """
        resolved_id = self._resolve_session_id(session_id)
        await self._redis.set(
            self._session_key(resolved_id),
            phpserialize.dumps(data),
            ex=self._config.session_expire,
        )
        if self._logger:
            self._logger.info("Session saved: %s", resolved_id[:8] + "...")

    async def delete(
        self,
        session_id: str | None = None,
    ) -> bool:
        """Delete a session.

        Args:
            session_id: Explicit session ID, or None to use contextvars.

        Returns:
            True if the session was deleted, False if it didn't exist.

        Raises:
            SessionContextError: If no session_id available.
        """
        resolved_id = self._resolve_session_id(session_id)
        result = await self._redis.delete(self._session_key(resolved_id))
        if self._logger:
            self._logger.info(
                "Session deleted: %s, existed=%s",
                resolved_id[:8] + "...",
                result > 0,
            )
        return result > 0

    async def exists(
        self,
        session_id: str | None = None,
    ) -> bool:
        """Check if a session exists.

        Args:
            session_id: Explicit session ID, or None to use contextvars.

        Returns:
            True if the session exists, False otherwise.

        Raises:
            SessionContextError: If no session_id available.
        """
        resolved_id = self._resolve_session_id(session_id)
        result = await self._redis.exists(self._session_key(resolved_id))
        return result > 0
