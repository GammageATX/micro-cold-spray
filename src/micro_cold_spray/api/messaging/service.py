"""Messaging service for pub/sub operations."""

from typing import Any, Dict, Callable, Set
import asyncio
from loguru import logger

from ..base import ConfigurableService
from ..config import ConfigService
from .models import MessageHandler
from micro_cold_spray.api.base.exceptions import ValidationError, MessageError


class MessagingService(ConfigurableService):
    """Service for handling pub/sub messaging."""
    
    def __init__(self, config_service: ConfigService):
        """Initialize messaging service.
        
        Args:
            config_service: Configuration service
        """
        super().__init__(service_name="messaging")
        self._config_service = config_service
        self._subscribers: Dict[str, Set[MessageHandler]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: Set[asyncio.Task] = set()
        self._valid_topics: Set[str] = set()
        self._shutdown_event = asyncio.Event()
        
    async def _start(self) -> None:
        """Start the messaging service."""
        try:
            # Initialize message handling
            self._subscribers = {}
            self._message_queue = asyncio.Queue()
            self._background_tasks = set()
            self._shutdown_event.clear()
            
            # Load valid topics from application config
            config = await self._config_service.get_config("application")
            services_config = config.data.get("services", {})
            message_config = services_config.get("message_broker", {})
            topic_groups = message_config.get("topics", {})
            
            # Flatten topic groups into a set of valid topics
            valid_topics = set()
            for group in topic_groups.values():
                valid_topics.update(group)
            
            # Set valid topics
            await self.set_valid_topics(valid_topics)
            
            # Initialize subscriber sets for each topic
            for topic in valid_topics:
                self._subscribers[topic] = set()
            
            # Start message processing task
            task = asyncio.create_task(self._process_messages())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            logger.info(f"Messaging service started with {len(self._valid_topics)} topics")
            
        except Exception as e:
            logger.error(f"Failed to start messaging service: {e}")
            raise MessageError("Failed to start messaging service", {"error": str(e)})

    async def _stop(self) -> None:
        """Stop the messaging service."""
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Cancel all background tasks
            for task in self._background_tasks:
                task.cancel()
            
            # Clear all subscribers
            self._subscribers.clear()
            
            # Clear message queue
            while not self._message_queue.empty():
                try:
                    self._message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                    
            logger.info("Messaging service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping messaging service: {e}")
            raise MessageError("Error stopping messaging service", {"error": str(e)})

    def _validate_topic(self, topic: str) -> None:
        """Validate topic name.
        
        Args:
            topic: Topic to validate
            
        Raises:
            MessageError: If topic is invalid
        """
        if not topic or not isinstance(topic, str):
            raise MessageError(
                "Invalid topic name",
                {"topic": topic, "type": type(topic)}
            )
            
        # Allow response topics if their base topic is valid
        if topic.endswith("/response"):
            base_topic = topic[:-9]  # Remove "/response"
            if base_topic in self._valid_topics:
                return
                
        if topic not in self._valid_topics:
            raise MessageError(
                f"Unknown topic: {topic}",
                {"topic": topic, "valid_topics": list(self._valid_topics)}
            )

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish message to topic."""
        try:
            self._validate_topic(topic)
            
            # Check if we have any subscribers before queueing
            if topic in self._subscribers and self._subscribers[topic]:
                await self._message_queue.put((topic, data))
                logger.debug(f"Published message to {topic}")
            else:
                logger.debug(f"No subscribers for topic {topic}, message dropped")
            
        except Exception as e:
            error_context = {
                "topic": topic,
                "data": data,
                "error": str(e)
            }
            logger.error("Failed to publish message", extra=error_context)
            raise MessageError("Failed to publish message", error_context)
            
    async def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to topic."""
        try:
            # Validate topic
            self._validate_topic(topic)
            
            # Validate callback
            if not callable(callback):
                raise ValidationError(
                    "Callback must be callable",
                    {"callback_type": type(callback)}
                )
                
            # Create handler
            handler = MessageHandler(callback=callback)
            handler.task = asyncio.create_task(self._handle_messages(handler))
            
            # Initialize subscriber set for topic if needed
            if topic not in self._subscribers:
                self._subscribers[topic] = set()
            
            # Add to subscribers
            self._subscribers[topic].add(handler)
            
            logger.debug(f"Subscribed to {topic}")
            
        except (ValidationError, MessageError):
            raise
        except Exception as e:
            error_context = {
                "topic": topic,
                "error": str(e)
            }
            logger.error("Failed to subscribe", extra=error_context)
            raise MessageError("Failed to subscribe", error_context)
            
    async def request(self, topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request and get response.
        
        Args:
            topic: Topic to send request to
            data: Request data
            
        Returns:
            Response data
            
        Raises:
            MessageError: If request fails
        """
        try:
            # Create response queue
            response_queue: asyncio.Queue = asyncio.Queue()
            
            # Create response handler
            async def response_handler(resp: Dict[str, Any]):
                await response_queue.put(resp)
            
            # Subscribe to response
            response_topic = f"{topic}/response"
            handler = MessageHandler(callback=response_handler)
            if response_topic not in self._subscribers:
                self._subscribers[response_topic] = set()
            self._subscribers[response_topic].add(handler)
            
            try:
                # Send request
                await self.publish(topic, data)
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(response_queue.get(), timeout=5.0)
                    return response
                except asyncio.TimeoutError:
                    raise MessageError("Request timed out")
                    
            finally:
                # Cleanup subscription
                if response_topic in self._subscribers:
                    self._subscribers[response_topic].discard(handler)
                    if not self._subscribers[response_topic]:
                        del self._subscribers[response_topic]
                
        except Exception as e:
            error_context = {
                "topic": topic,
                "data": data,
                "error": str(e)
            }
            logger.error("Failed to send request", extra=error_context)
            raise MessageError("Failed to send request", error_context)
            
    async def get_topics(self) -> Set[str]:
        """Get list of valid topics.
        
        Returns:
            Set of valid topics
            
        Raises:
            MessageError: If topics cannot be retrieved
        """
        return self._valid_topics
        
    async def set_valid_topics(self, topics: Set[str]) -> None:
        """Set valid topics.
        
        Args:
            topics: Set of valid topics
            
        Raises:
            MessageError: If topics cannot be set
        """
        try:
            self._valid_topics = topics
            logger.info(f"Updated valid topics: {topics}")
            
        except Exception as e:
            error_context = {
                "topics": topics,
                "error": str(e)
            }
            logger.error("Failed to set topics", extra=error_context)
            raise MessageError("Failed to set topics", error_context)
            
    async def get_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for topic.
        
        Args:
            topic: Topic to get subscribers for
            
        Returns:
            Number of subscribers
            
        Raises:
            MessageError: If subscriber count cannot be retrieved
        """
        try:
            return len(self._subscribers.get(topic, set()))
            
        except Exception as e:
            error_context = {
                "topic": topic,
                "error": str(e)
            }
            logger.error("Failed to get subscriber count", extra=error_context)
            raise MessageError("Failed to get subscriber count", error_context)
            
    async def _process_messages(self) -> None:
        """Process messages from queue."""
        while self.is_running:
            try:
                # Get next message
                topic, data = await self._message_queue.get()
                
                # Skip if no subscribers
                if topic not in self._subscribers or not self._subscribers[topic]:
                    logger.warning(f"No subscribers for topic: {topic}")
                    self._message_queue.task_done()
                    continue
                
                # Deliver to subscribers
                for handler in self._subscribers[topic]:
                    try:
                        await handler.queue.put(data)
                    except Exception as e:
                        logger.error(f"Failed to deliver message to handler: {e}")
                    
                self._message_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
            # Check for shutdown
            if self._shutdown_event.is_set():
                break
                
    async def _handle_messages(self, handler: MessageHandler) -> None:
        """Handle messages for subscriber.
        
        Args:
            handler: Message handler
        """
        while self.is_running:
            try:
                # Get next message
                data = await handler.queue.get()
                
                # Call callback
                await handler.callback(data)
                
                handler.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                
            # Check for shutdown
            if self._shutdown_event.is_set():
                break

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health status dictionary
        """
        try:
            return {
                "status": "ok" if self.is_running else "error",
                "topics": len(self._valid_topics),
                "active_subscribers": sum(len(subs) for subs in self._subscribers.values()),
                "background_tasks": len(self._background_tasks),
                "queue_size": self._message_queue.qsize()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
