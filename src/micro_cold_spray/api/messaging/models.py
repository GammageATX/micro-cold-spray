"""Messaging data models."""

from typing import Any, Dict, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from micro_cold_spray.api.base.exceptions import ValidationError, MessageError
from loguru import logger


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

    def __post_init__(self):
        """Validate handler after initialization."""
        if not callable(self.callback):
            raise ValidationError(
                "Message handler callback must be callable",
                {"callback_type": type(self.callback)}
            )
            
    def __hash__(self) -> int:
        """Hash based on callback function."""
        return hash(self.callback)
        
    def __eq__(self, other: object) -> bool:
        """Compare based on callback function."""
        if not isinstance(other, MessageHandler):
            return NotImplemented
        return self.callback == other.callback

    async def process_message(self, data: Dict[str, Any]) -> None:
        """Process a message through the handler."""
        try:
            self.stats.record_message()
            await self.callback(data)
            self.stats.record_processed()
        except Exception as e:
            self.stats.record_error()
            error_context = {
                "handler": self.__class__.__name__,
                "error": str(e)
            }
            logger.error("Message handler error", extra=error_context)
            raise MessageError("Message handler error", error_context)
