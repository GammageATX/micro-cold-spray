"""Messaging service."""

import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional
from datetime import datetime
import yaml
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error


MessageHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class MessagingService:
    """Messaging service."""
    
    def __init__(self):
        """Initialize service."""
        self.name = "messaging"
        self.version = "1.0.0"
        self.is_running = False
        self.config = {}
        self.topics: Dict[str, set[MessageHandler]] = {}
        self.message_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize service."""
        try:
            # Load config
            logger.info("Loading config from config/messaging.yaml")
            with open("config/messaging.yaml", "r") as f:
                self.config = yaml.safe_load(f)
            logger.debug(f"Loaded config: {self.config}")
            
            # Start message monitor
            self._monitor_task = asyncio.create_task(self._monitor_queue())
            self.is_running = True
            
            logger.info("Messaging service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to initialize messaging service: {e}"
            )
            
    async def stop(self) -> None:
        """Stop service."""
        try:
            # Stop message monitor
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None
            
            # Clear state
            self.topics.clear()
            self.is_running = False
            
            logger.info("Messaging service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop messaging service: {e}"
            )
            
    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="MessagingService not initialized"
            )
            
        return {
            "status": "healthy",
            "queue_size": self.message_queue.qsize(),
            "topic_count": len(self.topics),
            "timestamp": datetime.now().isoformat()
        }
            
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish message to topic."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="MessagingService not initialized"
            )
            
        # Validate topic
        if not self._is_valid_topic(topic):
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid topic: {topic}"
            )
            
        # Add message to queue
        await self.message_queue.put({
            "topic": topic,
            "data": message,
            "timestamp": datetime.now().isoformat()
        })
            
    async def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """Subscribe to topic."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="MessagingService not initialized"
            )
            
        # Validate topic
        if not self._is_valid_topic(topic):
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid topic: {topic}"
            )
            
        # Add handler
        if topic not in self.topics:
            self.topics[topic] = set()
        self.topics[topic].add(handler)
            
    def _is_valid_topic(self, topic: str) -> bool:
        """Check if topic is valid."""
        # Get valid topics from config
        topic_groups = self.config.get("message_broker", {}).get("topics", {})
        
        # Log config for debugging
        logger.debug(f"Topic groups: {topic_groups}")
        logger.debug(f"Checking topic: {topic}")
        
        # Check if topic exists in any group
        for group_name, topics in topic_groups.items():
            logger.debug(f"Checking group {group_name}: {topics}")
            if topic in topics:
                logger.debug(f"Topic {topic} found in group {group_name}")
                return True
                
        logger.debug(f"Topic {topic} not found in any group")
        return False
            
    async def _monitor_queue(self) -> None:
        """Monitor message queue."""
        try:
            while True:
                # Get next message
                message = await self.message_queue.get()
                topic = message["topic"]
                
                # Get handlers for topic
                handlers = self.topics.get(topic, set())
                
                # Dispatch message to handlers
                for handler in handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Handler error for topic {topic}: {e}")
                        
                # Mark message as done
                self.message_queue.task_done()
                
        except asyncio.CancelledError:
            logger.info("Message monitor stopped")
            raise
            
        except Exception as e:
            logger.error(f"Message monitor error: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Message monitor error: {e}"
            )
