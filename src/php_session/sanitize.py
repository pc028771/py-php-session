"""PHPSESSID sanitization and validation.

Provides security validation for PHP session IDs to prevent
injection attacks and other security vulnerabilities.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .constants import PHPSESSID_PATTERN

if TYPE_CHECKING:
    pass


def sanitize_phpsessid(
    session_id: str | None,
    logger: logging.Logger | None = None,
) -> str | None:
    """Sanitize and validate PHPSESSID for security.

    Args:
        session_id: Raw session ID from cookie or other source.
        logger: Optional logger for security warnings.

    Returns:
        Validated session ID or None if invalid.

    Security considerations:
        - Prevents injection attacks by validating format
        - Limits length to prevent DoS via large cookies
        - Only allows alphanumeric characters (no special chars)
        - Rejects empty strings, whitespace, and null bytes

    Example:
        >>> sanitize_phpsessid("abc123def456ghi789jkl012mno")
        'abc123def456ghi789jkl012mno'
        >>> sanitize_phpsessid("invalid<script>")
        None
    """
    if not session_id:
        return None

    # Strip whitespace (security: prevent bypass with padded IDs)
    session_id = session_id.strip()

    # Validate format (alphanumeric only, 26-128 chars)
    if not PHPSESSID_PATTERN.match(session_id):
        if logger:
            logger.warning(
                "Invalid PHPSESSID format rejected: prefix=%s, length=%d",
                session_id[:8] if len(session_id) >= 8 else session_id,
                len(session_id),
            )
        return None

    # Additional security: check for null bytes (shouldn't happen after regex, but defense in depth)
    if "\x00" in session_id:
        if logger:
            logger.warning("PHPSESSID with null byte rejected")
        return None

    return session_id
