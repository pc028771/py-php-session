"""Tests for context variable helpers."""

from __future__ import annotations

from php_session import get_current_session_id, set_current_session_id


class TestContextVars:
    """Tests for session_id context variable management."""

    def test_set_and_get_session_id(self) -> None:
        """Test setting and getting session_id via contextvars."""
        set_current_session_id("my_session_id_12345678901234567890")
        assert get_current_session_id() == "my_session_id_12345678901234567890"

    def test_get_session_id_returns_none_when_not_set(self) -> None:
        """Test that get_current_session_id returns None when not set."""
        set_current_session_id(None)
        assert get_current_session_id() is None

    def test_session_id_isolation_in_context(self) -> None:
        """Test that session_id can be updated."""
        set_current_session_id("session_1_abcdefghijklmnopqrstuvwxyz")
        assert get_current_session_id() == "session_1_abcdefghijklmnopqrstuvwxyz"

        set_current_session_id("session_2_zyxwvutsrqponmlkjihgfedcba")
        assert get_current_session_id() == "session_2_zyxwvutsrqponmlkjihgfedcba"
