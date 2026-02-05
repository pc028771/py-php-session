"""Tests for PHPSESSID sanitization."""

from __future__ import annotations

import logging

import pytest

from php_session import sanitize_phpsessid


class TestPHPSESSIDSanitization:
    """Test PHPSESSID sanitization for security."""

    def test_valid_session_id_32_chars(self) -> None:
        """Valid 32-char alphanumeric session ID should pass."""
        session_id = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        assert sanitize_phpsessid(session_id) == session_id

    def test_valid_session_id_26_chars(self) -> None:
        """Valid 26-char session ID (minimum) should pass."""
        session_id = "abcdef123456ghijkl78901234"
        assert sanitize_phpsessid(session_id) == session_id

    def test_valid_session_id_128_chars(self) -> None:
        """Valid 128-char session ID (maximum) should pass."""
        session_id = "a" * 128
        assert sanitize_phpsessid(session_id) == session_id

    def test_none_input(self) -> None:
        """None input should return None."""
        assert sanitize_phpsessid(None) is None

    def test_empty_string(self) -> None:
        """Empty string should return None."""
        assert sanitize_phpsessid("") is None

    def test_whitespace_only(self) -> None:
        """Whitespace-only string should return None."""
        assert sanitize_phpsessid("   ") is None

    def test_too_short(self) -> None:
        """Session ID shorter than 26 chars should be rejected."""
        session_id = "abc123"  # Only 6 chars
        assert sanitize_phpsessid(session_id) is None

    def test_too_long(self) -> None:
        """Session ID longer than 128 chars should be rejected."""
        session_id = "a" * 129
        assert sanitize_phpsessid(session_id) is None

    def test_sql_injection_attempt(self) -> None:
        """SQL injection attempt should be rejected."""
        session_id = "abc123' OR '1'='1"
        assert sanitize_phpsessid(session_id) is None

    def test_command_injection_attempt(self) -> None:
        """Command injection attempt should be rejected."""
        session_id = "abc123; rm -rf /"
        assert sanitize_phpsessid(session_id) is None

    def test_path_traversal_attempt(self) -> None:
        """Path traversal attempt should be rejected."""
        session_id = "../../../etc/passwd"
        assert sanitize_phpsessid(session_id) is None

    def test_special_characters(self) -> None:
        """Session ID with special characters should be rejected."""
        invalid_ids = [
            "abc123!@#$%^&*()",
            "abc123<script>",
            "abc123\n\r\t",
            "abc123,comma-dash",
            "abc123.dot",
        ]
        for session_id in invalid_ids:
            assert sanitize_phpsessid(session_id) is None, f"Should reject: {session_id}"

    def test_null_byte_injection(self) -> None:
        """Session ID with null byte should be rejected."""
        session_id = "abc123\x00hidden"
        assert sanitize_phpsessid(session_id) is None

    def test_unicode_characters(self) -> None:
        """Session ID with unicode should be rejected."""
        session_id = "abc123äöü"
        assert sanitize_phpsessid(session_id) is None

    def test_whitespace_padding_trimmed(self) -> None:
        """Valid session ID with whitespace padding should be trimmed and accepted."""
        session_id = "  " + "a" * 32 + "  "
        expected = "a" * 32
        assert sanitize_phpsessid(session_id) == expected

    def test_mixed_case_alphanumeric(self) -> None:
        """Mixed case alphanumeric should be accepted."""
        session_id = "AbCdEf123456GhIjKl78901234OpQr"
        assert sanitize_phpsessid(session_id) == session_id

    def test_all_numeric(self) -> None:
        """All numeric session ID should be accepted."""
        session_id = "1" * 32
        assert sanitize_phpsessid(session_id) == session_id

    def test_all_alpha(self) -> None:
        """All alphabetic session ID should be accepted."""
        session_id = "a" * 32
        assert sanitize_phpsessid(session_id) == session_id

    def test_boundary_25_chars(self) -> None:
        """25 chars (just below minimum) should be rejected."""
        session_id = "a" * 25
        assert sanitize_phpsessid(session_id) is None

    def test_boundary_26_chars(self) -> None:
        """26 chars (exact minimum) should be accepted."""
        session_id = "a" * 26
        assert sanitize_phpsessid(session_id) == session_id

    def test_boundary_128_chars(self) -> None:
        """128 chars (exact maximum) should be accepted."""
        session_id = "a" * 128
        assert sanitize_phpsessid(session_id) == session_id

    def test_boundary_129_chars(self) -> None:
        """129 chars (just above maximum) should be rejected."""
        session_id = "a" * 129
        assert sanitize_phpsessid(session_id) is None

    def test_xss_attempt(self) -> None:
        """XSS injection attempt should be rejected."""
        session_id = "<script>alert('xss')</script>"
        assert sanitize_phpsessid(session_id) is None

    def test_ldap_injection_attempt(self) -> None:
        """LDAP injection attempt should be rejected."""
        session_id = "admin)(|(password=*))"
        assert sanitize_phpsessid(session_id) is None

    def test_logger_called_on_invalid(self) -> None:
        """Logger should be called with warning for invalid session IDs."""
        logger = logging.getLogger("test")

        # Just verify it doesn't crash with logger and returns None
        result = sanitize_phpsessid("invalid<>", logger=logger)
        assert result is None

        # Also test with valid ID (shouldn't log warning)
        valid_result = sanitize_phpsessid("a" * 32, logger=logger)
        assert valid_result == "a" * 32
