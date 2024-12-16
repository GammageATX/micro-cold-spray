"""Messaging service implementation."""

from typing import Dict, Any, Set, Optional, Callable, Awaitable
from datetime import datetime
import asyncio
from loguru import logger

from micro_cold_spray.api.base.service import BaseService
from micro_cold_spray.api.base.exceptions import MessageError
from micro_cold_spray.api.config import ConfigService
from .models import MessageHandler


class MessagingService(BaseService):
    """Service for handling pub/sub messaging."""

    def __init__(self, config_service: ConfigService):
        """Initialize messaging service.
        
        Args:
            config_service: Configuration service instance
        """
        super().__init__("MessagingService")
        self._config_service = config_service
        self._valid_topics: Set[str] = set()
        self._handlers: Dict[str, Set[MessageHandler]] = {}
        self._background_tasks: Set[asyncio.Task] = set()
        self._queue_size = 0

    async def _start(self) -> None:
        """Start messaging service."""
        try:
            # Get valid topics from config
            config = await self._config_service.get_config("messaging")
            topics = config.data.get("services", {}).get("message_broker", {}).get("topics", {})
            
            # Flatten topic groups into set
            valid_topics = set()
            for group in topics.values():
                valid_topics.update(group)
                
            await self.set_valid_topics(valid_topics)
            
            # Start background monitoring task
            monitor_task = asyncio.create_task(self._monitor_queue())
            self.add_background_task(monitor_task)
            
            logger.info(f"Messaging service started with {len(valid_topics)} topics")
            
        except Exception as e:
            logger.error(f"Failed to start messaging service: {e}")
            raise

    async def _monitor_queue(self):
        """Background task to monitor queue size."""
        while True:
            try:
                await asyncio.sleep(1)
                # Log queue stats periodically
                logger.debug(f"Queue size: {self._queue_size}, Active tasks: {len(self._background_tasks)}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue monitor error: {e}")

    async def _stop(self) -> None:
        """Stop messaging service."""
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
        # Clear state
        self._valid_topics.clear()
        self._handlers.clear()
        self._background_tasks.clear()
        self._queue_size = 0
        
        logger.info("Messaging service stopped")

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health status information
        """
        try:
            return {
                "status": "ok",
                "topics": len(self._valid_topics),
                "active_subscribers": sum(len(handlers) for handlers in self._handlers.values()),
                "background_tasks": len(self._background_tasks),
                "queue_size": self._queue_size
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_topics(self) -> Set[str]:
        """Get set of valid topics.
        
        Returns:
            Set of valid topic names
        """
        return self._valid_topics.copy()

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish message to topic.
        
        Args:
            topic: Topic to publish to
            data: Message data
            
        Raises:
            MessageError: If topic is invalid or handler fails
        """
        if topic not in self._valid_topics:
            raise MessageError(
                "Unknown topic",
                {"topic": topic, "valid_topics": list(self._valid_topics)}
            )
            
        logger.debug(f"Published message to {topic}")
        
        # Process message through handlers
        handlers = self._handlers.get(topic, set())
        for handler in handlers:
            try:
                await handler.process_message(data)
            except MessageError as e:
                logger.error(f"Failed to publish message to {topic}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Failed to publish message to {topic}: {str(e)}")
                raise MessageError(
                    "Failed to publish message",
                    {"topic": topic, "error": str(e)}
                )

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Subscribe to topic.
        
        Args:
            topic: Topic to subscribe to
            callback: Async callback for handling messages
            
        Raises:
            MessageError: If topic is invalid
        """
        if topic not in self._valid_topics:
            raise MessageError(
                "Unknown topic",
                {"topic": topic, "valid_topics": list(self._valid_topics)}
            )
            
        # Create handler
        handler = MessageHandler(callback)
        
        # Add to handlers
        if topic not in self._handlers:
            self._handlers[topic] = set()
        self._handlers[topic].add(handler)
        
        logger.debug(f"Subscribed to {topic}")

    async def request(
        self,
        topic: str,
        data: Dict[str, Any],
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Send request and wait for response.
        
        Args:
            topic: Topic to send request to
            data: Request data
            timeout: Response timeout in seconds
            
        Returns:
            Response data
            
        Raises:
            MessageError: If request fails or times out
        """
        if topic not in self._valid_topics:
            raise MessageError(
                "Invalid topic",
                {"topic": topic, "valid_topics": list(self._valid_topics)}
            )
            
        # Create response future
        response_future = asyncio.Future()
        
        # Create response topic handler
        response_topic = f"{topic}/response"
        if response_topic not in self._valid_topics:
            raise MessageError(
                "Response topic not configured",
                {"topic": topic, "response_topic": response_topic}
            )
            
        async def response_handler(response_data: Dict[str, Any]):
            if not response_future.done():
                response_future.set_result(response_data)
                
        # Subscribe temporary handler
        await self.subscribe(response_topic, response_handler)
        
        try:
            # Send request
            await self.publish(topic, data)
            
            # Wait for response with timeout
            try:
                return await asyncio.wait_for(response_future, timeout)
            except asyncio.TimeoutError:
                raise MessageError(
                    "Request timed out",
                    {"topic": topic, "timeout": timeout}
                )
            
        except MessageError:
            raise
        except Exception as e:
            raise MessageError(
                "Request failed",
                {"topic": topic, "error": str(e)}
            )
        finally:
            # Cleanup handler
            if response_topic in self._handlers:
                self._handlers[response_topic].clear()

    async def get_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for topic.
        
        Args:
            topic: Topic to check
            
        Returns:
            Number of subscribers
            
        Raises:
            MessageError: If topic is invalid
        """
        if topic not in self._valid_topics:
            raise MessageError(
                "Invalid topic",
                {"topic": topic, "valid_topics": list(self._valid_topics)}
            )
            
        return len(self._handlers.get(topic, set()))

    async def set_valid_topics(self, topics: Set[str]) -> None:
        """Set valid topics.
        
        Args:
            topics: Set of valid topic names
        """
        self._valid_topics = topics.copy()
        logger.info(f"Updated valid topics: {topics}")

    def add_background_task(self, task: asyncio.Task) -> None:
        """Add background task.
        
        Args:
            task: Task to add
        """
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def increment_queue(self) -> None:
        """Increment queue size."""
        self._queue_size += 1

    def decrement_queue(self) -> None:
        """Decrement queue size."""
        self._queue_size = max(0, self._queue_size - 1)
