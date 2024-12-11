"""Messaging data models."""

from typing import Any, Dict, Callable
import asyncio
from dataclasses import dataclass


@dataclass
class MessageHandler:
    """Handler for subscribed messages."""
    callback: Callable[[Dict[str, Any]], None]
    queue: asyncio.Queue = asyncio.Queue()
    task: asyncio.Task | None = None
