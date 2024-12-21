"""Messaging data models."""

from typing import Any, Dict, Callable, Optional
from datetime import datetime
import asyncio
import inspect
from pydantic import BaseModel, Field
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error


class MessageStats(BaseModel):
    """Message handler statistics."""
    messages_received: int = Field(default=0, description="Number of messages received")
    messages_processed: int = Field(default=0, description="Number of messages processed")
    last_message_time: Optional[datetime] = Field(None, description="Timestamp of last message")
    errors: int = Field(default=0, description="Number of processing errors")
    created_at: datetime = Field(default_factory=datetime.now, description="Handler creation time")

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


class MessageHandler:
    """Handler for subscribed messages."""
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        """Initialize handler.
        
        Args:
            callback: Message processing callback
            
        Raises:
            HTTPException: If callback is invalid
        """
        if not callable(callback):
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Message handler callback must be callable, got {type(callback)}"
            )
        self.callback = callback
        self.queue: asyncio.Queue = asyncio.Queue()
        self.task: Optional[asyncio.Task] = None
        self.stats = MessageStats()
            
    def __hash__(self) -> int:
        """Hash based on callback function."""
        return hash(self.callback)
        
    def __eq__(self, other: object) -> bool:
        """Compare based on callback function."""
        if not isinstance(other, MessageHandler):
            return NotImplemented
        return self.callback == other.callback

    async def process_message(self, data: Dict[str, Any]) -> None:
        """Process a message through the handler.
        
        Args:
            data: Message data to process
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            self.stats.record_message()
            
            # Handle both async and sync callbacks
            if inspect.iscoroutinefunction(self.callback):
                await self.callback(data)
            else:
                self.callback(data)
                
            self.stats.record_processed()
            
        except Exception as e:
            self.stats.record_error()
            logger.error(f"Message handler error: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Message handler error: {e}"
            )
