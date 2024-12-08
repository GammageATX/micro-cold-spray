"""Message broker for pub/sub messaging."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional, Set
from loguru import logger

from micro_cold_spray.core.exceptions import MessageError, ConfigurationError


MessageHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class MessageBroker:
    """Message broker for pub/sub messaging."""

    def __init__(self, test_mode: bool = False) -> None:
        """Initialize message broker."""
        self._test_mode = test_mode
        self._valid_topics: Set[str] = set()
        self._subscribers: Dict[str, Set[MessageHandler]] = defaultdict(set)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._initialized = False
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._processing_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.debug(f"MessageBroker initialized in {'test' if test_mode else 'normal'} mode")

    def _ensure_event_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure there is a running event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    async def set_valid_topics(self, topics: Set[str]) -> None:
        """Set valid topics for message broker.

        Args:
            topics: Set of valid topic strings

        Raises:
            MessageError: If topics is empty or invalid
        """
        try:
            if not topics:
                raise ValueError("Topics set cannot be empty")

            self._valid_topics = topics
            # Initialize subscriber sets for all valid topics
            for topic in topics:
                if topic not in self._subscribers:
                    self._subscribers[topic] = set()

            logger.debug(f"Set valid topics: {topics}")

        except Exception as e:
            error_msg = f"Failed to set valid topics: {str(e)}"
            logger.error(error_msg)
            raise MessageError(error_msg) from e

    def _validate_topic(self, topic: str) -> None:
        """Validate topic against allowed patterns.

        Args:
            topic: Topic string to validate

        Raises:
            MessageError: If topic is invalid
        """
        # Error topic is always valid
        if topic == "error":
            return

        # In test mode, allow test/* topics
        if self._test_mode and topic.startswith("test/"):
            return

        # Must be initialized with valid topics
        if not self._initialized:
            raise MessageError("MessageBroker not initialized")

        # Check if topic is valid
        if topic not in self._valid_topics:
            raise MessageError(f"Invalid topic: {topic}")

    async def start(self) -> None:
        """Start message broker."""
        try:
            if not self._test_mode:
                # Set default valid topics in normal mode
                default_topics = {
                    "tag/request", "tag/response", "tag/update",
                    "config/request", "config/response", "config/update",
                    "state/request", "state/response", "state/change",
                    "sequence/request", "sequence/response", "sequence/state",
                    "sequence/progress", "sequence/step", "sequence/loaded",
                    "sequence/complete", "sequence/error", "sequence/status",
                    "pattern/request", "pattern/response", "pattern/state",
                    "action/request", "action/response", "action/state",
                    "parameter/request", "parameter/response", "parameter/state",
                    "validation/request", "validation/response",
                    "data/request", "data/response", "data/state",
                    "ui/request", "ui/response", "ui/state",
                    "hardware/state",
                    "motion/request", "motion/response", "motion/state",
                    "system/status", "system/state",
                    "error",
                    "action/group/request",
                    "action/group/response",
                    "action/group/state"
                }
                await self.set_valid_topics(default_topics)
                self._initialized = True

            # Start message processing
            if not self._running:
                self._running = True
                self._shutdown_event.clear()
                self._loop = self._ensure_event_loop()
                if not self._processing_task or self._processing_task.done():
                    self._processing_task = self._loop.create_task(self._process_messages())

            logger.debug("MessageBroker started")

        except Exception as e:
            error_msg = f"Failed to start MessageBroker: {str(e)}"
            logger.error(error_msg)
            raise MessageError(error_msg) from e

    async def _process_messages(self) -> None:
        """Process messages from the queue."""
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
        except Exception as e:
            logger.error(f"Message processing error: {e}")
        finally:
            self._running = False

    async def initialize(self) -> None:
        """Initialize message broker with valid topics from config."""
        try:
            # Get valid topics from application config
            app_config = await self._config_manager.get_config("application")
            if not app_config or "application" not in app_config:
                raise ConfigurationError("Invalid application config")

            topics_config = app_config["application"]["services"]["message_broker"]["topics"]
            if not topics_config:
                raise ConfigurationError("No topics defined in config")

            # Flatten topic lists into set
            valid_topics = set()
            for topic_group in topics_config.values():
                if isinstance(topic_group, list):
                    valid_topics.update(topic_group)

            # Add test topics in test mode
            if self._test_mode:
                valid_topics.update({
                    "test/request",
                    "test/response",
                    "test/state"
                })

            await self.set_valid_topics(valid_topics)
            self._initialized = True
            logger.debug(f"Initialized valid topics: {valid_topics}")

        except Exception as e:
            logger.error(f"Failed to initialize message broker: {e}")
            raise MessageError("Failed to initialize message broker") from e

    async def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """Subscribe to a topic.

        Args:
            topic: Topic to subscribe to
            handler: Async callback for messages

        Raises:
            MessageError: If topic is invalid or subscription fails
        """
        try:
            self._validate_topic(topic)
            if topic not in self._subscribers:
                self._subscribers[topic] = set()
            self._subscribers[topic].add(handler)
            logger.debug(f"Subscribed to topic: {topic}")

        except Exception as e:
            error_msg = f"Failed to subscribe to topic {topic}: {str(e)}"
            logger.error(error_msg)
            raise MessageError(error_msg) from e

    async def unsubscribe(self, topic: str, handler: MessageHandler) -> None:
        """Unsubscribe from a topic.

        Args:
            topic: Topic to unsubscribe from
            handler: Handler to remove

        Raises:
            MessageError: If topic is invalid or unsubscribe fails
        """
        try:
            self._validate_topic(topic)
            if topic in self._subscribers and handler in self._subscribers[topic]:
                self._subscribers[topic].remove(handler)
                logger.debug(f"Unsubscribed from topic: {topic}")

        except Exception as e:
            error_msg = f"Failed to unsubscribe from topic {topic}: {str(e)}"
            logger.error(error_msg)
            raise MessageError(error_msg) from e

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publish message to topic.

        Args:
            topic: Topic to publish to
            data: Message data dictionary

        Raises:
            MessageError: If topic is invalid or publish fails
        """
        try:
            # Skip validation for error topic
            if topic != "error":
                self._validate_topic(topic)

            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()

            # Put message in queue
            await self._message_queue.put((topic, data))
            logger.debug(f"Published to topic {topic}: {data}")

        except MessageError as e:
            # Don't wrap MessageError, but ensure error propagation
            error_context = {
                "source": "message_broker",
                "error": str(e),
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            if "request_id" in data:
                error_context["request_id"] = data["request_id"]

            try:
                await self.publish("error", error_context)
            except Exception as err:
                logger.error(f"Failed to publish error: {err}")
            raise e

        except Exception as e:
            error_msg = f"Failed to publish to topic {topic}: {str(e)}"
            error_context = {
                "source": "message_broker",
                "error": error_msg,
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            if "request_id" in data:
                error_context["request_id"] = data["request_id"]

            try:
                await self.publish("error", error_context)
            except Exception as err:
                logger.error(f"Failed to publish error: {err}")
            raise MessageError(error_msg) from e

    async def _deliver_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Deliver a message to all subscribers of a topic.

        Args:
            topic: Topic to deliver to
            data: Message data dictionary
        """
        if not self._subscribers[topic]:
            return

        tasks = []
        loop = self._ensure_event_loop()

        for handler in self._subscribers[topic]:
            task = loop.create_task(handler(data))
            tasks.append(task)

        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                error_msg = f"Message delivery timeout for topic {topic}"
                logger.error(error_msg)
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await self.publish("error", {
                    "source": "message_broker",
                    "error": error_msg,
                    "topic": topic,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                error_msg = f"Error delivering message to topic {topic}: {str(e)}"
                logger.error(error_msg)
                await self.publish("error", {
                    "source": "message_broker",
                    "error": error_msg,
                    "topic": topic,
                    "timestamp": datetime.now().isoformat()
                })

    async def shutdown(self) -> None:
        """Shutdown message broker."""
        try:
            logger.debug("Shutting down MessageBroker")
            self._running = False
            self._shutdown_event.set()
            await self._stop_processing_task()
            await self._clear_message_queue()
            self._subscribers.clear()
            self._initialized = False
            logger.debug("MessageBroker shutdown complete")
        except Exception as e:
            logger.error(f"Error during MessageBroker shutdown: {e}")
            raise MessageError("Failed to shutdown MessageBroker") from e

    async def _stop_processing_task(self) -> None:
        """Stop the message processing task."""
        if self._processing_task and not self._processing_task.done():
            try:
                self._processing_task.cancel()
                await asyncio.wait_for(self._processing_task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.error(f"Error stopping processing task: {e}")
            finally:
                self._processing_task = None

    async def _clear_message_queue(self) -> None:
        """Clear all messages from the queue."""
        try:
            while True:
                self._message_queue.get_nowait()
                self._message_queue.task_done()
        except asyncio.QueueEmpty:
            pass


# Sequence Topics
SEQUENCE_TOPICS = {
    # Commands
    "sequence/request": {  # Start, stop, pause, resume
        "request_type": str,  # "start", "stop", "pause", "resume"
        "request_id": str,
        "timestamp": str
    },
    "sequence/response": {  # Command acknowledgments
        "request_id": str,
        "success": bool,
        "error": Optional[str],
        "timestamp": str
    },

    # State & Progress
    "sequence/state": {  # Complete sequence state
        "state": str,  # "IDLE", "RUNNING", "PAUSED", "COMPLETED", "ERROR"
        "current_step": Optional[Dict],  # Current step info if running
        "step_index": Optional[int],  # Current step index if running
        "total_steps": Optional[int],  # Total steps in sequence
        "progress": Optional[float],  # Overall progress 0-100
        "estimated_remaining": Optional[int],  # Seconds remaining
        "error": Optional[str],  # Error message if state is ERROR
        "timestamp": str
    },

    # Step Details
    "sequence/step": {  # Step state changes
        "step": Dict,  # Step configuration
        "state": str,  # "STARTED", "IN_PROGRESS", "COMPLETED", "ERROR"
        "progress": Optional[float],  # Step progress 0-100
        "message": Optional[str],  # Status message
        "error": Optional[str],  # Error details if failed
        "timestamp": str
    }
}
