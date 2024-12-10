from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
import asyncio
from loguru import logger
import uuid
from collections import defaultdict

from ..base import BaseService

class MessagingError(Exception):
    def __init__(self, message: str, context: Dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context if context is not None else {}

class MessagingService(BaseService):
    """Service for handling pub/sub messaging."""

    def __init__(self):
        super().__init__(service_name="messaging")
        self._valid_topics: Set[str] = set()
        self._subscribers: Dict[str, Set[MessageHandler]] = defaultdict(set)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._processing_task: Optional[asyncio.Task] = None

        # Default topics from message_broker.py
        self._default_topics = {
            "tag/request", "tag/response", "tag/update",
            "config/request", "config/response", "config/update",
            "state/request", "state/response", "state/change",
            "sequence/request", "sequence/response", "sequence/state",
            # ... (copy all default topics)
        }

    async def start(self) -> None:
        """Initialize messaging service."""
        await super().start()
        try:
            # Start with default topics
            await self.set_valid_topics(self._default_topics)
            
            # Start message processing
            self._running = True
            self._shutdown_event.clear()
            self._processing_task = asyncio.create_task(self._process_messages())
            
            logger.info("Messaging service started")
            
        except Exception as e:
            raise MessagingError(f"Failed to start: {str(e)}")

    async def set_valid_topics(self, topics: Set[str]) -> None:
        """Set valid topics."""
        try:
            if not topics:
                raise MessagingError("Topics set cannot be empty")
                
            self._valid_topics = topics
            # Initialize subscriber sets
            for topic in topics:
                if topic not in self._subscribers:
                    self._subscribers[topic] = set()
                    
        except Exception as e:
            raise MessagingError(f"Failed to set topics: {str(e)}")

    async def _process_messages(self) -> None:
        """Process messages from queue."""
        try:
            while self._running and not self._shutdown_event.is_set():
                try:
                    topic, message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=0.1
                    )
                    await self._deliver_message(topic, message)
                    self._message_queue.task_done()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except asyncio.CancelledError:
            logger.debug("Message processing cancelled")
        finally:
            self._running = False

    async def _deliver_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Deliver message to subscribers."""
        if not self._subscribers[topic]:
            return

        tasks = []
        for handler in self._subscribers[topic]:
            task = asyncio.create_task(handler(data))
            tasks.append(task)

        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Message delivery timeout: {topic}")
                for task in tasks:
                    if not task.done():
                        task.cancel()
            except Exception as e:
                logger.error(f"Error delivering message: {e}") 

    async def get_queue_size(self) -> int:
        """Get current message queue size."""
        return self._message_queue.qsize()

    async def clear_queue(self) -> None:
        """Clear message queue."""
        try:
            while True:
                self._message_queue.get_nowait()
                self._message_queue.task_done()
        except asyncio.QueueEmpty:
            pass

    async def stop(self) -> None:
        """Stop messaging service."""
        try:
            self._running = False
            self._shutdown_event.set()
            
            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
            
            await self.clear_queue()
            self._subscribers.clear()
            
            logger.info("Messaging service stopped")
            
        except Exception as e:
            raise MessagingError(f"Failed to stop: {str(e)}") 