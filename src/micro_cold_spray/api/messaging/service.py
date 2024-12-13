"""Messaging service for pub/sub operations."""

from typing import Any, Dict, Callable, Set
import asyncio
from loguru import logger
from collections import defaultdict
from pathlib import Path
import yaml
import json
import jsonschema
from datetime import datetime

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
        self.is_running = False
        self.start_time = datetime.now()
        self._subscribers = defaultdict(set)
        self._valid_topics = set()
        self._shutdown_event = asyncio.Event()
        
    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self.is_running and not self._shutdown_event.is_set()

    async def stop(self) -> None:
        """Stop the messaging service."""
        try:
            self.is_running = False
            self._shutdown_event.set()
            
            # Wait for message queue to empty
            if not self._message_queue.empty():
                await self._message_queue.join()
                
            # Cancel all subscriber tasks
            for handlers in self._subscribers.values():
                for handler in handlers:
                    if handler.task:
                        handler.task.cancel()
                        
            logger.info("Messaging service stopped")
            
        except Exception as e:
            error_context = {"error": str(e)}
            logger.error("Failed to stop messaging service", extra=error_context)
            raise MessageError("Failed to stop messaging service", error_context)
        
    async def _start(self) -> None:
        """Initialize messaging service."""
        try:
            # Load schema first
            schema_path = Path("config/schemas/messaging.json")
            if schema_path.exists():
                with open(schema_path) as f:
                    self._schema = json.load(f)
            
            # Load config (YAML)
            app_config = await self._config_service.get_config("application")
            if isinstance(app_config, str):
                # If returned as YAML string, parse it
                app_config = yaml.safe_load(app_config)
                
            message_broker_config = app_config.get("services", {}).get("message_broker", {})
            
            # Validate against schema if available
            if hasattr(self, '_schema'):
                try:
                    jsonschema.validate(message_broker_config, self._schema)
                except jsonschema.exceptions.ValidationError as e:
                    raise ValidationError(f"Config validation failed: {str(e)}")
            
            # Extract topics
            topics = set()
            for topic_group in message_broker_config.get("topics", {}).values():
                if isinstance(topic_group, (list, set)):
                    topics.update(topic_group)
                elif isinstance(topic_group, dict):
                    topics.update(topic_group.keys())
            
            self._valid_topics = topics
            logger.debug(f"Loaded {len(self._valid_topics)} valid topics")
            
            # Start message processing
            self.is_running = True
            asyncio.create_task(self._process_messages())
            
            logger.info("Messaging service started")
            
        except Exception as e:
            error_context = {
                "source": "messaging_service",
                "error": str(e)
            }
            logger.error("Failed to start messaging service", extra=error_context)
            raise MessageError("Failed to start messaging service", error_context)
            
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
            
        if topic not in self._valid_topics:
            raise MessageError(
                f"Unknown topic: {topic}",
                {"topic": topic, "valid_topics": list(self._valid_topics)}
            )

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish message to topic."""
        try:
            self._validate_topic(topic)
            await self._message_queue.put((topic, data))
            logger.debug(f"Published message to {topic}")
            
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
            
            # Subscribe to response
            response_topic = f"{topic}/response"
            await self.subscribe(response_topic, lambda resp: response_queue.put_nowait(resp))
            
            # Send request
            await self.publish(topic, data)
            
            # Wait for response
            try:
                response = await asyncio.wait_for(response_queue.get(), timeout=5.0)
                return response
            except asyncio.TimeoutError:
                raise MessageError("Request timed out")
                
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
            return len(self._subscribers[topic])
            
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
                
                # Deliver to subscribers
                for handler in self._subscribers[topic]:
                    await handler.queue.put(data)
                    
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
