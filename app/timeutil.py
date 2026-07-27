"""Unix-time helpers. All API datetimes are UTC epoch seconds (int)."""

from __future__ import annotations

import time


def unix_now() -> int:
    """Current UTC epoch seconds."""
    return int(time.time())
