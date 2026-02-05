"""Tests for SessionManager class."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import phpserialize
import pytest

from php_session import (
    SessionConfig,
    SessionContextError,
    SessionLockError,
    SessionManager,
    set_current_session_id,
)
from php_session.decode import decode_json_fields


class TestSessionManagerInit:
    """Tests for SessionManager initialization."""

    def test_init_registers_lua_script(self, mock_redis: AsyncMock) -> None:
        """Test that __init__ registers the Lua release lock script."""
        manager = SessionManager(mock_redis)
        assert manager._release_lock_script is not None

    def test_session_key_format(self, session_manager: SessionManager) -> None:
        """Test that session key follows PHP format."""
        key = session_manager._session_key("abc123")
        assert key == "PHPREDIS_SESSION:abc123"

    def test_lock_key_format(self, session_manager: SessionManager) -> None:
        """Test that lock key follows PHP format with _LOCK suffix."""
        key = session_manager._lock_key("abc123")
        assert key == "PHPREDIS_SESSION:abc123_LOCK"


class TestSessionManagerGet:
    """Tests for SessionManager.get() method."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_session_not_found(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test get() returns None when session doesn't exist."""
        mock_redis.get.return_value = None

        result = await session_manager.get()

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_returns_full_session_data(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test get() returns full session dict when no key specified."""
        session_data: dict[str, Any] = {"user_id": 123, "cart_count": 5}
        mock_redis.get.return_value = phpserialize.dumps(session_data)

        result = await session_manager.get()

        assert result == session_data

    @pytest.mark.asyncio
    async def test_get_returns_specific_key(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test get() returns specific key value when key specified."""
        session_data: dict[str, Any] = {"user_id": 123, "cart_count": 5}
        mock_redis.get.return_value = phpserialize.dumps(session_data)

        result = await session_manager.get("cart_count")

        assert result == 5

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test get() returns None when specific key doesn't exist."""
        session_data: dict[str, Any] = {"user_id": 123}
        mock_redis.get.return_value = phpserialize.dumps(session_data)

        result = await session_manager.get("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_raises_when_no_session_id(
        self, session_manager: SessionManager
    ) -> None:
        """Test get() raises SessionContextError when no session_id in context."""
        set_current_session_id(None)

        with pytest.raises(SessionContextError):
            await session_manager.get()

    @pytest.mark.asyncio
    async def test_get_with_explicit_session_id(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test get() works with explicit session_id parameter."""
        set_current_session_id(None)  # Clear context
        session_data: dict[str, Any] = {"user_id": 456}
        mock_redis.get.return_value = phpserialize.dumps(session_data)

        result = await session_manager.get(session_id="explicit_id_12345678901234567890")

        assert result == session_data


class TestSessionManagerSet:
    """Tests for SessionManager.set() method."""

    @pytest.mark.asyncio
    async def test_set_creates_new_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test set() creates new session when none exists."""
        mock_redis.get.return_value = None

        await session_manager.set("cart_count", 5)

        # Verify set was called with serialized data
        call_args = mock_redis.set.call_args
        assert call_args is not None
        saved_data = phpserialize.loads(call_args[0][1], decode_strings=True)
        assert saved_data == {"cart_count": 5}

    @pytest.mark.asyncio
    async def test_set_updates_existing_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test set() updates existing session data."""
        existing_data: dict[str, Any] = {"user_id": 123, "cart_count": 3}
        mock_redis.get.return_value = phpserialize.dumps(existing_data)

        await session_manager.set("cart_count", 10)

        call_args = mock_redis.set.call_args
        assert call_args is not None
        saved_data = phpserialize.loads(call_args[0][1], decode_strings=True)
        assert saved_data == {"user_id": 123, "cart_count": 10}

    @pytest.mark.asyncio
    async def test_set_with_explicit_session_id(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test set() works with explicit session_id parameter."""
        set_current_session_id(None)
        mock_redis.get.return_value = None

        await session_manager.set("key", "value", session_id="explicit_id_1234567890123456")

        call_args = mock_redis.set.call_args
        assert call_args is not None
        assert "explicit_id_1234567890123456" in call_args[0][0]


class TestSessionManagerSave:
    """Tests for SessionManager.save() method."""

    @pytest.mark.asyncio
    async def test_save_writes_entire_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test save() writes complete session data."""
        new_data: dict[str, Any] = {"user_id": 456, "name": "test"}

        await session_manager.save(new_data)

        call_args = mock_redis.set.call_args
        assert call_args is not None
        saved_data = phpserialize.loads(call_args[0][1], decode_strings=True)
        assert saved_data == new_data


class TestSessionManagerLock:
    """Tests for SessionManager.lock() context manager."""

    @pytest.mark.asyncio
    async def test_lock_acquires_and_releases(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test lock() acquires lock on enter and releases on exit."""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None

        async with session_manager.lock() as session:
            assert isinstance(session, dict)

        # Verify lock was acquired with NX and PX
        lock_call = mock_redis.set.call_args_list[0]
        assert lock_call[1]["nx"] is True
        assert "px" in lock_call[1]

        # Verify Lua script was called to release lock
        session_manager._release_lock_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_loads_existing_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test lock() loads existing session data."""
        mock_redis.set.return_value = True
        existing_data: dict[str, Any] = {"user_id": 789, "cart_count": 2}
        mock_redis.get.return_value = phpserialize.dumps(existing_data)

        async with session_manager.lock() as session:
            assert session["user_id"] == 789
            assert session["cart_count"] == 2

    @pytest.mark.asyncio
    async def test_lock_saves_modified_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test lock() auto-saves modified session on exit."""
        mock_redis.set.return_value = True
        initial_data: dict[str, Any] = {"cart_count": 1}
        mock_redis.get.return_value = phpserialize.dumps(initial_data)

        async with session_manager.lock() as session:
            session["cart_count"] = 99
            session["new_field"] = "hello"

        # Find the session save call (not the lock call)
        save_calls = [
            c for c in mock_redis.set.call_args_list
            if "_LOCK" not in str(c[0][0])
        ]
        assert len(save_calls) == 1
        saved_data = phpserialize.loads(save_calls[0][0][1], decode_strings=True)
        assert saved_data["cart_count"] == 99
        assert saved_data["new_field"] == "hello"

    @pytest.mark.asyncio
    async def test_lock_uses_unique_token(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test lock() uses a unique token for each acquisition."""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None
        tokens: list[str] = []

        # Capture tokens from two lock acquisitions
        async with session_manager.lock():
            lock_call = mock_redis.set.call_args_list[0]
            tokens.append(str(lock_call[0][1]))

        mock_redis.set.reset_mock()

        async with session_manager.lock():
            lock_call = mock_redis.set.call_args_list[0]
            tokens.append(str(lock_call[0][1]))

        # Tokens should be different
        assert tokens[0] != tokens[1]
        # Tokens should be hex strings (32 chars for 16 bytes)
        assert len(tokens[0]) == 32
        assert len(tokens[1]) == 32

    @pytest.mark.asyncio
    async def test_lock_timeout_raises_error(
        self, mock_redis: AsyncMock
    ) -> None:
        """Test lock() raises SessionLockError when lock cannot be acquired."""
        mock_redis.set.return_value = False  # Lock never acquired

        config = SessionConfig(session_expire=3600, lock_timeout=0.1)
        manager = SessionManager(mock_redis, config)

        with pytest.raises(SessionLockError):
            async with manager.lock():
                pass

    @pytest.mark.asyncio
    async def test_lock_releases_on_exception(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test lock() releases lock even when exception occurs."""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None

        with pytest.raises(ValueError):
            async with session_manager.lock():
                raise ValueError("Test error")

        # Lock should still be released via Lua script
        session_manager._release_lock_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_retries_on_contention(
        self, mock_redis: AsyncMock
    ) -> None:
        """Test lock() retries when lock is held by another process."""
        # First two attempts fail, third succeeds, fourth is session save
        mock_redis.set.side_effect = [False, False, True, True]
        mock_redis.get.return_value = None

        config = SessionConfig(session_expire=3600, lock_timeout=1.0)
        manager = SessionManager(mock_redis, config)

        async with manager.lock():
            pass

        # Should have tried 3 times for lock + 1 for session save
        assert mock_redis.set.call_count == 4

    @pytest.mark.asyncio
    async def test_lock_with_explicit_session_id(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test lock() works with explicit session_id parameter."""
        set_current_session_id(None)
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None

        async with session_manager.lock(session_id="explicit_lock_id_1234567890123456") as session:
            session["test"] = "value"

        # Verify the explicit session ID was used
        lock_call = mock_redis.set.call_args_list[0]
        assert "explicit_lock_id_1234567890123456" in str(lock_call[0][0])


class TestSessionManagerDelete:
    """Tests for SessionManager.delete() method."""

    @pytest.mark.asyncio
    async def test_delete_existing_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test delete() returns True for existing session."""
        mock_redis.delete.return_value = 1

        result = await session_manager.delete()

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test delete() returns False for nonexistent session."""
        mock_redis.delete.return_value = 0

        result = await session_manager.delete()

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_with_explicit_session_id(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test delete() works with explicit session_id parameter."""
        set_current_session_id(None)
        mock_redis.delete.return_value = 1

        result = await session_manager.delete(session_id="to_delete_id_1234567890123456")

        assert result is True
        call_args = mock_redis.delete.call_args
        assert "to_delete_id_1234567890123456" in str(call_args[0][0])


class TestSessionManagerExists:
    """Tests for SessionManager.exists() method."""

    @pytest.mark.asyncio
    async def test_exists_returns_true(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test exists() returns True for existing session."""
        mock_redis.exists.return_value = 1

        result = await session_manager.exists()

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test exists() returns False for nonexistent session."""
        mock_redis.exists.return_value = 0

        result = await session_manager.exists()

        assert result is False


class TestDecodeJsonFields:
    """Tests for decode_json_fields helper function."""

    def test_decodes_known_json_fields(self) -> None:
        """Test that known JSON fields are decoded."""
        data: dict[str, Any] = {
            "scart_items": '["item1", "item2"]',
            "ga_data": '{"event": "click"}',
            "user_id": 123,
        }

        result = decode_json_fields(
            data,
            json_fields=frozenset({"scart_items", "ga_data"}),
        )

        assert result["scart_items"] == ["item1", "item2"]
        assert result["ga_data"] == {"event": "click"}
        assert result["user_id"] == 123

    def test_decodes_trace_list_fields(self) -> None:
        """Test that trace_list_* fields are decoded."""
        data: dict[str, Any] = {
            "trace_list_products": "[1, 2, 3]",
            "trace_list_categories": '{"a": 1}',
        }

        result = decode_json_fields(data, json_prefix="trace_list_")

        assert result["trace_list_products"] == [1, 2, 3]
        assert result["trace_list_categories"] == {"a": 1}

    def test_handles_invalid_json_gracefully(self) -> None:
        """Test that invalid JSON is left as-is."""
        data: dict[str, Any] = {
            "scart_items": "not valid json {",
            "user_name": "John",
        }

        result = decode_json_fields(
            data,
            json_fields=frozenset({"scart_items"}),
        )

        assert result["scart_items"] == "not valid json {"
        assert result["user_name"] == "John"

    def test_skips_non_string_values(self) -> None:
        """Test that non-string values are not decoded."""
        data: dict[str, Any] = {
            "scart_items": 123,
            "ga_data": ["already", "parsed"],
        }

        result = decode_json_fields(
            data,
            json_fields=frozenset({"scart_items", "ga_data"}),
        )

        assert result["scart_items"] == 123
        assert result["ga_data"] == ["already", "parsed"]

    def test_empty_dict_returns_empty(self) -> None:
        """Test that empty dict returns empty dict."""
        result = decode_json_fields({})
        assert result == {}


class TestPHPCompatibility:
    """Tests for PHP serialization compatibility."""

    @pytest.mark.asyncio
    async def test_reads_php_serialized_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test reading session data serialized by PHP."""
        php_data = b'a:2:{s:7:"user_id";i:123;s:4:"name";s:4:"John";}'
        mock_redis.get.return_value = php_data

        result = await session_manager.get()

        assert result is not None
        assert result["user_id"] == 123
        assert result["name"] == "John"

    @pytest.mark.asyncio
    async def test_writes_php_compatible_session(
        self, session_manager: SessionManager, mock_redis: AsyncMock
    ) -> None:
        """Test that written session can be read by PHP."""
        mock_redis.get.return_value = None

        await session_manager.set("cart_count", 5)

        call_args = mock_redis.set.call_args
        assert call_args is not None
        serialized: bytes = call_args[0][1]

        # Verify it can be deserialized
        deserialized = phpserialize.loads(serialized, decode_strings=True)
        assert deserialized["cart_count"] == 5
