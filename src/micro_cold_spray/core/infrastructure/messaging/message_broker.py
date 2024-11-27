"""Message broker for system-wide messaging.

Special Note:
    MessageBroker loads its config directly from messaging.yaml to avoid circular dependencies.
    This is an intentional exception to our normal ConfigManager pattern because:
    1. MessageBroker is a core infrastructure component
    2. ConfigManager needs MessageBroker to publish updates
    3. Other components still use ConfigManager as the source of truth
"""
from typing import Dict, Any, Callable, Awaitable, Optional
from collections import defaultdict
import asyncio
from loguru import logger

from ...exceptions import MessageBrokerError

MessageHandler = Callable[[Dict[str, Any]], Awaitable[None]]

class MessageBroker:
    """
    Handles all pub/sub messaging for the application.
    Provides a central communication hub for all components.
    """

    def __init__(self):
        """Initialize the message broker."""
        self._subscribers: Dict[str, set[MessageHandler]] = defaultdict(set)
        self._running = False
        self._message_queue: asyncio.Queue[tuple[str, Dict[str, Any]]] = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        logger.info("MessageBroker initialized")

    async def start(self) -> None:
        """Start the message processing loop."""
        try:
            if self._running:
                logger.warning("MessageBroker already running")
                return

            self._running = True
            self._processing_task = asyncio.create_task(self._process_messages())
            logger.info("MessageBroker started")

        except Exception as e:
            logger.exception("Failed to start MessageBroker")
            raise MessageBrokerError("Failed to start message broker") from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the message broker."""
        try:
            logger.info("Shutting down MessageBroker")
            self._running = False
            
            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass

            # Clear any remaining messages
            while not self._message_queue.empty():
                try:
                    self._message_queue.get_nowait()
                    self._message_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            self._subscribers.clear()
            logger.info("MessageBroker shutdown complete")

        except Exception as e:
            logger.exception("Error during MessageBroker shutdown")
            raise MessageBrokerError("Failed to shutdown message broker") from e

    async def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """
        Subscribe to a topic with a message handler.
        
        Args:
            topic: The topic to subscribe to
            handler: Async callback function to handle messages
        """
        try:
            if not callable(handler):
                raise ValueError("Handler must be callable")
            
            self._subscribers[topic].add(handler)
            logger.debug(f"Subscribed to topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {e}")
            raise MessageBrokerError(f"Subscription failed: {str(e)}") from e

    async def unsubscribe(self, topic: str, handler: MessageHandler) -> None:
        """
        Unsubscribe a handler from a topic.
        
        Args:
            topic: The topic to unsubscribe from
            handler: The handler to remove
        """
        try:
            if topic in self._subscribers:
                self._subscribers[topic].discard(handler)
                if not self._subscribers[topic]:
                    del self._subscribers[topic]
                logger.debug(f"Unsubscribed from topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic {topic}: {e}")
            raise MessageBrokerError(f"Unsubscribe failed: {str(e)}") from e

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic to publish to
            message: The message data to publish
        """
        try:
            await self._message_queue.put((topic, message))
            logger.debug(f"Published message to topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to publish to topic {topic}: {e}")
            raise MessageBrokerError(f"Publish failed: {str(e)}") from e

    async def _process_messages(self) -> None:
        """Process messages from the queue and distribute to subscribers."""
        try:
            while self._running:
                try:
                    topic, message = await self._message_queue.get()
                    
                    if topic in self._subscribers:
                        subscriber_tasks = []
                        for handler in self._subscribers[topic]:
                            task = asyncio.create_task(self._safe_handle_message(handler, message))
                            subscriber_tasks.append(task)
                        
                        if subscriber_tasks:
                            await asyncio.gather(*subscriber_tasks)
                    
                    self._message_queue.task_done()

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await asyncio.sleep(0.1)  # Brief pause on error

        except asyncio.CancelledError:
            logger.info("Message processing loop cancelled")
            raise
        except Exception as e:
            logger.exception("Fatal error in message processing loop")
            raise MessageBrokerError("Message processing loop failed") from e

    async def _safe_handle_message(self, handler: MessageHandler, message: Dict[str, Any]) -> None:
        """Safely execute a message handler with error handling."""
        try:
            await handler(message)
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            # Don't re-raise to prevent breaking the message loop

    async def request(self, topic: str, message: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """
        Send a request and wait for a response.
        
        Args:
            topic: The request topic
            message: The request message
            timeout: Maximum time to wait for response in seconds
            
        Returns:
            The response message
        """
        try:
            response_future: asyncio.Future = asyncio.Future()
            
            async def response_handler(response_msg: Dict[str, Any]) -> None:
                if not response_future.done():
                    response_future.set_result(response_msg)
            
            response_topic = f"{topic}/response"
            await self.subscribe(response_topic, response_handler)
            
            try:
                await self.publish(topic, message)
                return await asyncio.wait_for(response_future, timeout)
                
            finally:
                await self.unsubscribe(response_topic, response_handler)

        except asyncio.TimeoutError:
            logger.error(f"Request timeout for topic {topic}")
            raise MessageBrokerError(f"Request timeout: {topic}")
        except Exception as e:
            logger.error(f"Request failed for topic {topic}: {e}")
            raise MessageBrokerError(f"Request failed: {str(e)}") from e