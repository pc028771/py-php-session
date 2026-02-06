"""JSON field decoding utilities.

Some PHP session variables store JSON strings that need parsing.
This module handles automatic decoding of known JSON fields.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any


def decode_json_fields(
    data: dict[str, Any],
    json_fields: frozenset[str] | None = None,
    json_prefix: str | None = "trace_list_",
) -> dict[str, Any]:
    """Decode JSON-encoded fields in session data.

    Some PHP session variables store JSON strings that need parsing.
    This function automatically decodes known JSON fields.

    Args:
        data: Raw session data dictionary.
        json_fields: Set of field names known to contain JSON.
                    If None, no specific fields are decoded.
        json_prefix: Prefix pattern for auto-detecting JSON fields.
                    Fields starting with this prefix will be decoded.
                    Set to None to disable prefix matching.

    Returns:
        Session data with JSON fields decoded.

    Example:
        >>> data = {"cart": '["item1", "item2"]', "count": 5}
        >>> decode_json_fields(data, json_fields=frozenset({"cart"}))
        {'cart': ['item1', 'item2'], 'count': 5}
    """
    for key, value in data.items():
        if not isinstance(value, str):
            continue

        # Check known JSON fields or prefix pattern
        should_decode = (json_fields and key in json_fields) or (
            json_prefix and key.startswith(json_prefix)
        )

        if not should_decode:
            continue

        with contextlib.suppress(json.JSONDecodeError, ValueError):
            data[key] = json.loads(value)

    return data
