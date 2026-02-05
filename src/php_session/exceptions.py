"""Custom exceptions for PHP session management.

Provides a hierarchy of exceptions for better error handling
in session operations.
"""

from __future__ import annotations


class SessionError(Exception):
    """Base exception for session-related errors.

    All session-specific exceptions inherit from this class,
    allowing callers to catch all session errors with a single except clause.
    """


class SessionLockError(SessionError):
    """Raised when session lock cannot be acquired.

    This typically occurs when:
    - Another process holds the lock for too long
    - Lock timeout is reached
    - Redis connection issues during lock acquisition

    Attributes:
        session_id: The session ID that couldn't be locked (truncated for security).
        timeout: The timeout value that was exceeded.
    """

    def __init__(
        self,
        session_id: str,
        timeout: float,
        message: str | None = None,
    ) -> None:
        self.session_id = session_id[:8] + "..." if len(session_id) > 8 else session_id
        self.timeout = timeout
        if message is None:
            message = f"Could not acquire session lock for {self.session_id} within {timeout}s"
        super().__init__(message)


class SessionNotFoundError(SessionError):
    """Raised when a session does not exist.

    This is raised when operations require an existing session
    but none is found in Redis.

    Attributes:
        session_id: The session ID that wasn't found (truncated for security).
    """

    def __init__(
        self,
        session_id: str,
        message: str | None = None,
    ) -> None:
        self.session_id = session_id[:8] + "..." if len(session_id) > 8 else session_id
        if message is None:
            message = f"Session not found: {self.session_id}"
        super().__init__(message)


class SessionContextError(SessionError):
    """Raised when session_id is not available in context.

    This occurs when session operations are attempted without
    a session ID being set (either via middleware or explicitly).
    """

    def __init__(self, message: str | None = None) -> None:
        if message is None:
            message = "No session_id in context - middleware not set up or session_id not provided"
        super().__init__(message)
