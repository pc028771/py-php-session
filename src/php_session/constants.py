"""Constants for PHP session management.

These constants match PHP's redis session handler configuration,
ensuring compatibility between Python and PHP session handling.
"""

from __future__ import annotations

import re
from typing import Final

# PHP redis session handler default prefix (configurable via session.save_path?prefix=)
SESSION_PREFIX: Final[str] = "PHPREDIS_SESSION:"

# PHP redis lock key suffix: {session_key}_LOCK
LOCK_SUFFIX: Final[str] = "_LOCK"

# Default known JSON-encoded session fields (auto-decoded when reading)
# These are commonly used in PHP applications that store JSON in session
DEFAULT_JSON_FIELDS: frozenset[str] = frozenset(
    {
        "scart_items",
        "ga_data",
        "session_view_log",
        "MPIReceive",
    }
)

# Lua script for safe lock release
# Matches PHP redis session handler's lock release mechanism exactly:
# - Only releases if token matches (prevents releasing other process's lock)
# - Uses atomic EVAL to prevent race conditions
RELEASE_LOCK_SCRIPT: Final[str] = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# PHP session ID validation pattern
# Default PHP session IDs are 26-128 alphanumeric characters (letters, digits, comma, dash)
# Restrict to safer alphanumeric only for security (prevents injection attacks)
PHPSESSID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9]{26,128}$")

# Default session expiration in seconds (24 hours, matching PHP default)
DEFAULT_SESSION_EXPIRE: Final[int] = 86400

# Default lock timeout in seconds
DEFAULT_LOCK_TIMEOUT: Final[float] = 30.0

# Lock retry interval in seconds (like PHP)
LOCK_RETRY_INTERVAL: Final[float] = 0.05
