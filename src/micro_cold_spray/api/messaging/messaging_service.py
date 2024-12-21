"""Messaging service implementation."""

from typing import Dict, Any, Set, Callable, Awaitable
import asyncio
import os
from loguru import logger
from fastapi import status
import yaml

from micro_cold_spray.api.base.base_errors import create_error
from .messaging_models import MessageHandler


class MessagingService:
    """Service for handling pub/sub messaging."""

    def __init__(self):
        """Initialize messaging service."""
        self._valid_topics: Set[str] = set()
        self._handlers: Dict[str, Set[MessageHandler]] = {}
        self._background_tasks: Set[asyncio.Task] = set()
        self._queue_size = 0
        self._is_running = False
        self._version = "1.0.0"

    async def initialize(self) -> None:
        """Initialize service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            # Get valid topics from config
            config = await self._load_config()
            topics = config.get("message_broker", {}).get("topics", {})
            
            # Flatten topic groups into set
            valid_topics = set()
            for group in topics.values():
                valid_topics.update(group)
                
            await self.set_valid_topics(valid_topics)
            
            # Configure the service with messaging config
            messaging_config = config.get("message_broker", {})
            await self.configure(messaging_config)
            
            # Start background monitoring task
            monitor_task = asyncio.create_task(self._monitor_queue())
            self.add_background_task(monitor_task)
            
            self._is_running = True
            logger.info(f"Messaging service started with {len(valid_topics)} topics")
            
        except Exception as e:
            logger.error(f"Failed to initialize messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to initialize messaging service: {e}"
            )

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

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
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
            self._is_running = False
            
            logger.info("Messaging service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop messaging service: {e}"
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health status information
            
        Raises:
            HTTPException: If health check fails
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
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Health check failed: {e}"
            )

    async def get_topics(self) -> Set[str]:
        """Get set of valid topics.
        
        Returns:
            Set of valid topic names
            
        Raises:
            HTTPException: If service unavailable
        """
        try:
            return self._valid_topics.copy()
        except Exception as e:
            logger.error(f"Failed to get topics: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to get topics: {e}"
            )

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish message to topic.
        
        Args:
            topic: Topic to publish to
            data: Message data
            
        Raises:
            HTTPException: If topic is invalid or handler fails
        """
        if topic not in self._valid_topics:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Unknown topic: {topic}"
            )
            
        logger.debug(f"Published message to {topic}")
        
        # Process message through handlers
        handlers = self._handlers.get(topic, set())
        for handler in handlers:
            try:
                await handler.process_message(data)
            except Exception as e:
                if isinstance(e, create_error):
                    raise e
                logger.error(f"Failed to publish message: {e}")
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Failed to publish message to {topic}: {e}"
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
            HTTPException: If topic is invalid
        """
        if topic not in self._valid_topics:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Unknown topic: {topic}"
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
            HTTPException: If request fails or times out
        """
        if topic not in self._valid_topics:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Invalid topic: {topic}"
            )
            
        # Create response future
        response_future = asyncio.Future()
        
        # Create response topic handler
        response_topic = f"{topic}/response"
        if response_topic not in self._valid_topics:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Response topic not configured: {response_topic}"
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
                raise create_error(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    message=f"Request timed out for topic {topic}"
                )
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            logger.error(f"Request failed: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Request failed for topic {topic}: {e}"
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
            HTTPException: If topic is invalid
        """
        if topic not in self._valid_topics:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Invalid topic: {topic}"
            )
            
        return len(self._handlers.get(topic, set()))

    async def set_valid_topics(self, topics: Set[str]) -> None:
        """Set valid topics.
        
        Args:
            topics: Set of valid topic names
            
        Raises:
            HTTPException: If update fails
        """
        try:
            self._valid_topics = topics.copy()
            logger.info(f"Updated valid topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to update topics: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update topics: {e}"
            )

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

    @property
    def name(self) -> str:
        """Get service name."""
        return "messaging"

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def _load_config(self) -> Dict[str, Any]:
        """Load configuration.
        
        Returns:
            Dict[str, Any]: Configuration data
            
        Raises:
            HTTPException: If config loading fails
        """
        try:
            # Get config path
            config_path = os.path.join(os.getcwd(), "config", "messaging.yaml")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Messaging config file not found at {config_path}")
            
            # Load config from file
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                
            if not isinstance(config, dict):
                raise ValueError("Invalid messaging configuration format")
                
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to load configuration: {e}"
            )

    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure service.
        
        Args:
            config: Configuration data
            
        Raises:
            HTTPException: If configuration fails
        """
        try:
            # Apply configuration
            if "queue_size" in config:
                self._queue_size = config["queue_size"]
            logger.info(f"Service configured with queue size: {self._queue_size}")
        except Exception as e:
            logger.error(f"Failed to configure service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to configure service: {e}"
            )
