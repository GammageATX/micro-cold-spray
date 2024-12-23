"""Monitoring utilities."""

import time
from typing import Dict, Any
from loguru import logger


_start_time = time.time()


def get_uptime() -> float:
    """Get service uptime in seconds.
    
    Returns:
        Uptime in seconds
    """
    return time.time() - _start_time
