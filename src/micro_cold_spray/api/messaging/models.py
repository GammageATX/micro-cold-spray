"""Messaging data models."""

from typing import Any, Dict, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


@dataclass
class MessageStats:
    """Message handler statistics."""
    messages_received: int = 0
    messages_processed: int = 0
    last_message_time: Optional[datetime] = None
    errors: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def record_message(self) -> None:
        """Record received message."""
        self.messages_received += 1
        self.last_message_time = datetime.now()

    def record_processed(self) -> None:
        """Record processed message."""
        self.messages_processed += 1

    def record_error(self) -> None:
        """Record processing error."""
        self.errors += 1


@dataclass
class MessageHandler:
    """Handler for subscribed messages."""
    callback: Callable[[Dict[str, Any]], None]
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: Optional[asyncio.Task] = None
    stats: MessageStats = field(default_factory=MessageStats)

    async def process_message(self, data: Dict[str, Any]) -> None:
        """Process a message through the handler.
        
        Args:
            data: Message data to process
        """
        try:
            self.stats.record_message()
            await self.callback(data)
            self.stats.record_processed()
        except Exception:
            self.stats.record_error()
            raise
