"""Tests for messaging service."""

import pytest
from unittest.mock import AsyncMock
import asyncio

from micro_cold_spray.api.base.exceptions import MessageError
from micro_cold_spray.api.messaging.service import MessagingService
from micro_cold_spray.api.config import ConfigService


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock(spec=ConfigService)
    
    # Mock application config
    service.get_config.return_value.data = {
        "services": {
            "message_broker": {
                "topics": {
                    "test_group": ["test/topic", "test/response"],
                    "control": ["control/start", "control/stop"]
                }
            }
        }
    }
    
    return service


@pytest.fixture
async def messaging_service(mock_config_service):
    """Create messaging service instance."""
    service = MessagingService(config_service=mock_config_service)
    await service.start()
    yield service
    await service.stop()


class TestMessagingService:
    """Test messaging service functionality."""

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_config_service):
        """Test service startup and shutdown."""
        service = MessagingService(config_service=mock_config_service)

        # Test startup
        await service.start()
        assert service.is_running
        assert len(service._valid_topics) == 4
        assert len(service._background_tasks) > 0

        # Test shutdown
        await service.stop()
        assert not service.is_running
        assert len(service._valid_topics) == 0
        assert len(service._background_tasks) == 0

    @pytest.mark.asyncio
    async def test_start_config_error(self, mock_config_service):
        """Test startup with config error."""
        mock_config_service.get_config.side_effect = Exception("Config error")
        service = MessagingService(config_service=mock_config_service)

        with pytest.raises(Exception) as exc_info:
            await service.start()
        assert "Config error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_publish_subscribe(self, messaging_service):
        """Test publish/subscribe functionality."""
        received_data = None
        event = asyncio.Event()

        async def callback(data):
            nonlocal received_data
            received_data = data
            event.set()

        # Subscribe to topic
        await messaging_service.subscribe("test/topic", callback)

        # Publish message
        test_data = {"key": "value"}
        await messaging_service.publish("test/topic", test_data)

        # Wait for callback
        await event.wait()
        assert received_data == test_data

    @pytest.mark.asyncio
    async def test_publish_invalid_topic(self, messaging_service):
        """Test publishing to invalid topic."""
        with pytest.raises(MessageError) as exc_info:
            await messaging_service.publish("invalid/topic", {})
        assert "Unknown topic" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_subscribe_invalid_topic(self, messaging_service):
        """Test subscribing to invalid topic."""
        async def callback(data):
            pass

        with pytest.raises(MessageError) as exc_info:
            await messaging_service.subscribe("invalid/topic", callback)
        assert "Unknown topic" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_subscribe_invalid_callback(self, messaging_service):
        """Test subscribing with invalid callback."""
        with pytest.raises(Exception) as exc_info:
            await messaging_service.subscribe("test/topic", "not_callable")
        assert "Message handler callback must be callable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_response(self, messaging_service):
        """Test request/response pattern."""
        # Setup responder
        response_event = asyncio.Event()

        async def response_handler(data):
            # Echo request data with response flag
            response_data = {**data, "is_response": True}
            await messaging_service.publish("test/response", response_data)
            response_event.set()

        await messaging_service.subscribe("test/topic", response_handler)

        # Send request
        request_data = {"key": "value"}
        response = await messaging_service.request("test/topic", request_data)
        
        # Wait for response handler
        await response_event.wait()
        
        assert response["is_response"]
        assert response["key"] == "value"

    @pytest.mark.asyncio
    async def test_request_timeout(self, messaging_service):
        """Test request timeout."""
        # Setup non-responding handler
        async def no_response(data):
            await asyncio.sleep(6)  # Longer than timeout

        await messaging_service.subscribe("test/topic", no_response)

        with pytest.raises(MessageError) as exc_info:
            await messaging_service.request("test/topic", {"key": "value"}, timeout=0.1)
        assert "Request timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, messaging_service):
        """Test multiple subscribers for same topic."""
        received_count = 0
        event = asyncio.Event()

        async def callback(data):
            nonlocal received_count
            received_count += 1
            if received_count == 2:
                event.set()

        # Add two subscribers
        await messaging_service.subscribe("test/topic", callback)
        await messaging_service.subscribe("test/topic", callback)

        # Publish message
        await messaging_service.publish("test/topic", {"key": "value"})

        # Wait for both callbacks
        await event.wait()
        assert received_count == 2

    @pytest.mark.asyncio
    async def test_subscriber_error_handling(self, messaging_service):
        """Test error handling in subscriber callback."""
        error_count = 0
        event = asyncio.Event()

        async def error_callback(data):
            nonlocal error_count
            error_count += 1
            event.set()
            raise Exception("Test error")

        # Subscribe error-raising handler
        await messaging_service.subscribe("test/topic", error_callback)

        # Publish message
        with pytest.raises(MessageError) as exc_info:
            await messaging_service.publish("test/topic", {"key": "value"})
        
        # Wait for callback
        await event.wait()
        
        assert error_count == 1
        assert "Message handler error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_subscriber_count(self, messaging_service):
        """Test subscriber count tracking."""
        async def callback(data):
            pass

        # Initially no subscribers
        assert await messaging_service.get_subscriber_count("test/topic") == 0

        # Add subscribers
        await messaging_service.subscribe("test/topic", callback)
        await messaging_service.subscribe("test/topic", callback)
        assert await messaging_service.get_subscriber_count("test/topic") == 2

    @pytest.mark.asyncio
    async def test_health_check(self, messaging_service):
        """Test service health check."""
        async def callback(data):
            pass

        # Add some subscribers
        await messaging_service.subscribe("test/topic", callback)
        await messaging_service.subscribe("control/start", callback)

        health = await messaging_service.check_health()

        assert health["status"] == "ok"
        assert health["topics"] == 4
        assert health["active_subscribers"] == 2
        assert health["background_tasks"] > 0
        assert health["queue_size"] == 0
