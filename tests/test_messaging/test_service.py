"""Tests for messaging service."""

import pytest
from unittest.mock import AsyncMock, patch
import asyncio
from typing import Dict, Any

from micro_cold_spray.api.messaging.service import MessagingService
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.base.exceptions import MessageError


class TestMessagingService:
    """Test messaging service functionality."""

    @pytest.fixture
    def mock_config_service(self):
        """Create mock config service."""
        mock = AsyncMock(spec=ConfigService)
        mock.get_config.return_value = AsyncMock(
            data={
                "services": {
                    "message_broker": {
                        "topics": {
                            "test": ["test/topic", "test/topic/response"],
                            "control": ["control/start", "control/stop"]
                        }
                    }
                }
            }
        )
        return mock

    @pytest.fixture
    async def service(self, mock_config_service):
        """Create messaging service instance."""
        service = MessagingService(mock_config_service)
        await service.start()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_init_and_start(self, mock_config_service):
        """Test service initialization and startup."""
        service = MessagingService(mock_config_service)
        assert service._config_service == mock_config_service
        assert not service._valid_topics
        assert not service._handlers
        assert not service._background_tasks
        assert service._queue_size == 0

        await service.start()
        assert len(service._valid_topics) == 4
        assert "test/topic" in service._valid_topics
        assert "test/topic/response" in service._valid_topics
        assert "control/start" in service._valid_topics
        assert "control/stop" in service._valid_topics
        assert len(service._background_tasks) == 1  # Monitor task

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_error(self, mock_config_service):
        """Test service startup error handling."""
        mock_config_service.get_config.side_effect = Exception("Config error")
        service = MessagingService(mock_config_service)

        with pytest.raises(Exception) as exc_info:
            await service.start()
        assert "Config error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_monitor_queue_error(self, service):
        """Test monitor queue error handling."""
        # Create a task that will raise an error
        async def error_task():
            raise Exception("Monitor error")

        task = asyncio.create_task(error_task())
        service.add_background_task(task)

        # Wait for error to be logged
        await asyncio.sleep(0.5)
        await service.stop()

    @pytest.mark.asyncio
    async def test_monitor_queue_cancel(self, service):
        """Test monitor queue cancellation."""
        # Get the monitor task
        monitor_task = next(iter(service._background_tasks))
        
        # Cancel the task
        monitor_task.cancel()
        
        # Wait for cancellation to be processed
        await asyncio.sleep(0.5)
        await service.stop()

    @pytest.mark.asyncio
    async def test_monitor_queue_exception(self, service):
        """Test monitor queue exception handling."""
        # Create a monitor task that will raise an exception
        async def error_monitor():
            while True:
                raise Exception("Monitor error")

        # Replace the existing monitor task
        monitor_task = next(iter(service._background_tasks))
        monitor_task.cancel()
        service._background_tasks.remove(monitor_task)

        # Add our error-raising monitor task
        error_task = asyncio.create_task(error_monitor())
        service.add_background_task(error_task)

        # Wait for error to be logged
        await asyncio.sleep(0.5)
        await service.stop()

    @pytest.mark.asyncio
    async def test_monitor_queue_sleep_error(self, service):
        """Test monitor queue sleep error handling."""
        # Mock asyncio.sleep to raise an error
        async def mock_sleep(*args):
            raise Exception("Sleep error")

        # Replace the existing monitor task
        monitor_task = next(iter(service._background_tasks))
        monitor_task.cancel()
        service._background_tasks.remove(monitor_task)

        # Create new monitor task with mocked sleep
        with patch("asyncio.sleep", side_effect=mock_sleep):
            monitor_task = asyncio.create_task(service._monitor_queue())
            service.add_background_task(monitor_task)

            # Wait briefly for the task to start
            try:
                await asyncio.sleep(0.1)
            except Exception:
                pass
            
            # Verify task is still running despite sleep error
            assert not monitor_task.done()
            assert monitor_task in service._background_tasks

            # Cleanup
            monitor_task.cancel()
            try:
                await monitor_task
            except (asyncio.CancelledError, Exception):
                pass
            await service.stop()

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check functionality."""
        # Test healthy state
        health = await service.check_health()
        assert health["status"] == "ok"
        assert health["topics"] == 4
        assert health["active_subscribers"] == 0
        assert health["background_tasks"] == 1
        assert health["queue_size"] == 0

        # Test with error
        class MockTopics:
            def __len__(self):
                raise Exception("Test error")

        with patch.object(service, "_valid_topics", new=MockTopics()):
            health = await service.check_health()
            assert health["status"] == "error"
            assert "Test error" in health["error"]

    @pytest.mark.asyncio
    async def test_get_topics(self, service):
        """Test getting valid topics."""
        topics = await service.get_topics()
        assert len(topics) == 4
        assert "test/topic" in topics
        assert "test/topic/response" in topics
        assert "control/start" in topics
        assert "control/stop" in topics

    @pytest.mark.asyncio
    async def test_publish_subscribe(self, service):
        """Test publish-subscribe functionality."""
        received_messages = []
        
        async def test_callback(data: Dict[str, Any]):
            received_messages.append(data)

        # Subscribe to topic
        await service.subscribe("test/topic", test_callback)
        assert await service.get_subscriber_count("test/topic") == 1

        # Publish message
        test_data = {"key": "value"}
        await service.publish("test/topic", test_data)
        
        # Allow time for message processing
        await asyncio.sleep(0.5)
        
        assert len(received_messages) == 1
        assert received_messages[0] == test_data

    @pytest.mark.asyncio
    async def test_publish_handler_error(self, service):
        """Test publish with handler error."""
        # Handler that raises a MessageError
        async def error_handler1(data: Dict[str, Any]):
            raise MessageError("Message handler error", {"data": data})

        # Handler that raises a generic error
        async def error_handler2(data: Dict[str, Any]):
            raise ValueError("Generic error")

        # Test MessageError propagation
        await service.subscribe("test/topic", error_handler1)
        with pytest.raises(MessageError) as exc_info:
            await service.publish("test/topic", {"key": "value"})
        assert "Message handler error" in str(exc_info.value)

        # Test generic error conversion to MessageError
        await service.subscribe("test/topic", error_handler2)
        with pytest.raises(MessageError) as exc_info:
            await service.publish("test/topic", {"key": "value"})
        assert "Message handler error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_publish_handler_cleanup(self, service):
        """Test handler cleanup after error."""
        # Handler that raises an error
        async def error_handler(data: Dict[str, Any]):
            raise ValueError("Handler error")

        # Subscribe handler
        await service.subscribe("test/topic", error_handler)

        # Publish message (should fail)
        with pytest.raises(MessageError):
            await service.publish("test/topic", {"key": "value"})

        # Verify handler was cleaned up
        assert len(service._handlers["test/topic"]) == 1  # Handler should still exist
        handler = next(iter(service._handlers["test/topic"]))
        assert handler.stats.errors == 1  # Error count should be incremented

    @pytest.mark.asyncio
    async def test_publish_handler_error_cleanup(self, service):
        """Test handler error cleanup."""
        # Handler that raises an error
        async def error_handler(data: Dict[str, Any]):
            raise ValueError("Handler error")

        # Subscribe handler
        await service.subscribe("test/topic", error_handler)

        # Mock handler.process_message to raise an error
        async def mock_process_message(*args, **kwargs):
            handler.stats.errors += 1
            raise Exception("Process error")

        handler = next(iter(service._handlers["test/topic"]))
        with patch.object(handler, "process_message", side_effect=mock_process_message):
            # Publish message (should fail)
            with pytest.raises(MessageError):
                await service.publish("test/topic", {"key": "value"})

            # Verify handler error was logged
            assert handler.stats.errors == 1

    @pytest.mark.asyncio
    async def test_publish_invalid_topic(self, service):
        """Test publishing to invalid topic."""
        with pytest.raises(MessageError) as exc_info:
            await service.publish("invalid/topic", {"key": "value"})
        assert "Unknown topic" in str(exc_info.value)
        assert "invalid/topic" in exc_info.value.context["topic"]

    @pytest.mark.asyncio
    async def test_subscribe_invalid_topic(self, service):
        """Test subscribing to invalid topic."""
        async def test_callback(data): pass
        
        with pytest.raises(MessageError) as exc_info:
            await service.subscribe("invalid/topic", test_callback)
        assert "Unknown topic" in str(exc_info.value)
        assert "invalid/topic" in exc_info.value.context["topic"]

    @pytest.mark.asyncio
    async def test_request_response(self, service):
        """Test request-response pattern."""
        # Setup response handler
        async def response_handler(data: Dict[str, Any]):
            response_data = {"response": "test"}
            await service.publish("test/topic/response", response_data)

        await service.subscribe("test/topic", response_handler)

        # Send request
        response = await service.request("test/topic", {"key": "value"})
        assert response == {"response": "test"}

    @pytest.mark.asyncio
    async def test_request_errors(self, service):
        """Test request error handling."""
        # Test invalid topic
        with pytest.raises(MessageError) as exc_info:
            await service.request("invalid/topic", {"key": "value"})
        assert "Invalid topic" in str(exc_info.value)

        # Test missing response topic
        with patch.object(service, "_valid_topics", new={"test/topic"}):
            with pytest.raises(MessageError) as exc_info:
                await service.request("test/topic", {"key": "value"})
            assert "Response topic not configured" in str(exc_info.value)

        # Test request failure
        async def failing_handler(data: Dict[str, Any]):
            raise ValueError("Handler error")

        await service.subscribe("test/topic", failing_handler)
        with pytest.raises(MessageError) as exc_info:
            await service.request("test/topic", {"key": "value"})
        assert "Message handler error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_timeout(self, service):
        """Test request timeout."""
        # Setup slow handler that never sends response
        async def slow_handler(data: Dict[str, Any]):
            await asyncio.sleep(2)  # Longer than timeout

        await service.subscribe("test/topic", slow_handler)

        # Request should timeout before handler finishes
        with pytest.raises(MessageError) as exc_info:
            await service.request("test/topic", {"key": "value"}, timeout=0.1)
        assert "Request timed out" in str(exc_info.value)
        assert exc_info.value.context["timeout"] == 0.1

    @pytest.mark.asyncio
    async def test_request_cleanup(self, service):
        """Test request handler cleanup."""
        # Setup handler that raises an error
        async def error_handler(data: Dict[str, Any]):
            raise ValueError("Handler error")

        await service.subscribe("test/topic", error_handler)

        # Send request (should fail)
        with pytest.raises(MessageError):
            await service.request("test/topic", {"key": "value"})

        # Verify response handler was cleaned up
        assert not service._handlers["test/topic/response"]

    @pytest.mark.asyncio
    async def test_request_error_cleanup(self, service):
        """Test request error cleanup."""
        # Setup handler that raises an error
        async def error_handler(data: Dict[str, Any]):
            raise ValueError("Handler error")

        await service.subscribe("test/topic", error_handler)

        # Mock publish to raise an error
        async def mock_publish(*args, **kwargs):
            raise MessageError("Publish error")

        with patch.object(service, "publish", side_effect=mock_publish):
            # Send request (should fail)
            with pytest.raises(MessageError):
                await service.request("test/topic", {"key": "value"})

            # Verify response handler was cleaned up
            assert not service._handlers["test/topic/response"]

    @pytest.mark.asyncio
    async def test_request_publish_error(self, service):
        """Test request publish error handling."""
        # Setup handler that raises an error
        async def error_handler(data: Dict[str, Any]):
            raise ValueError("Handler error")

        await service.subscribe("test/topic", error_handler)

        # Mock publish to raise a generic error
        async def mock_publish(*args, **kwargs):
            raise Exception("Publish error")

        with patch.object(service, "publish", side_effect=mock_publish):
            # Send request (should fail)
            with pytest.raises(MessageError) as exc_info:
                await service.request("test/topic", {"key": "value"})
            assert "Request failed" in str(exc_info.value)
            assert "Publish error" in exc_info.value.context["error"]

    @pytest.mark.asyncio
    async def test_subscriber_count(self, service):
        """Test subscriber count tracking."""
        async def callback1(data): pass
        async def callback2(data): pass

        assert await service.get_subscriber_count("test/topic") == 0

        await service.subscribe("test/topic", callback1)
        assert await service.get_subscriber_count("test/topic") == 1

        await service.subscribe("test/topic", callback2)
        assert await service.get_subscriber_count("test/topic") == 2

    @pytest.mark.asyncio
    async def test_set_valid_topics(self, service):
        """Test updating valid topics."""
        new_topics = {"topic1", "topic2", "topic3"}
        await service.set_valid_topics(new_topics)
        
        assert await service.get_topics() == new_topics
        assert service._valid_topics == new_topics

    @pytest.mark.asyncio
    async def test_background_tasks(self, service):
        """Test background task management."""
        # Create test task
        async def test_task():
            await asyncio.sleep(0.5)

        task = asyncio.create_task(test_task())
        initial_task_count = len(service._background_tasks)

        # Add task
        service.add_background_task(task)
        assert len(service._background_tasks) == initial_task_count + 1

        # Wait for task completion
        await task
        await asyncio.sleep(0.5)  # Allow callback to execute
        assert len(service._background_tasks) == initial_task_count  # Task should be removed

    @pytest.mark.asyncio
    async def test_queue_size_tracking(self, service):
        """Test queue size tracking."""
        assert service._queue_size == 0

        service.increment_queue()
        assert service._queue_size == 1

        service.increment_queue()
        assert service._queue_size == 2

        service.decrement_queue()
        assert service._queue_size == 1

        service.decrement_queue()
        assert service._queue_size == 0

        # Test underflow protection
        service.decrement_queue()
        assert service._queue_size == 0
