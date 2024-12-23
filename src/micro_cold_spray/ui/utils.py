"""UI utilities."""

import time
from typing import Optional

# Track service start time for uptime calculation
_START_TIME: Optional[float] = None


def get_uptime() -> float:
    """Get service uptime in seconds."""
    global _START_TIME
    if _START_TIME is None:
        _START_TIME = time.time()
    return time.time() - _START_TIME
