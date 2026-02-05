"""Context variable helpers for session ID management.

Uses Python's contextvars to store the current request's session ID,
enabling dependency injection without explicit parameter passing.
"""

from __future__ import annotations

from contextvars import ContextVar

# ContextVar for current request's session_id (DI pattern)
_current_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)


def set_current_session_id(session_id: str | None) -> None:
    """Set session_id for current request (called by middleware).

    Args:
        session_id: The session ID to set, or None to clear.
    """
    _current_session_id.set(session_id)


def get_current_session_id() -> str | None:
    """Get session_id for current request.

    Returns:
        The current session ID, or None if not set.
    """
    return _current_session_id.get()
