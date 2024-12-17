"""Tests for messaging router."""

import pytest
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect
from datetime import datetime
from unittest.mock import AsyncMock, patch

from micro_cold_spray.api.messaging.router import get_service, lifespan
from micro_cold_spray.api.base.exceptions import MessageError, ConfigurationError
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    service.is_initialized = True
    service.is_running = True
    
    # Mock get_config to return proper config data
    async def mock_get_config(config_type: str):
        return ConfigData(
            metadata=ConfigMetadata(
                config_type=config_type,
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={
                "services": {
                    "message_broker": {
                        "topics": {
                            "system": ["state", "health", "control"],
                            "data": ["spray", "position", "pressure"]
                        },
                        "max_subscribers": 10,
                        "timeout": 5.0
                    }
                }
            }
        )
    service.get_config.side_effect = mock_get_config
    return service


@pytest.fixture
def mock_messaging_service(mock_config_service):
    """Create mock messaging service with config."""
    service = AsyncMock()
    service.is_initialized = True
    service.is_running = True
    service._service_name = "MessagingService"
    service.version = "1.0.0"
    service.uptime = "0:00:00"
    service._config_service = mock_config_service
    
    # Mock health check method
    async def mock_check_health():
        return {
            "status": "healthy",
            "service_info": {
                "name": service._service_name,
                "version": service.version,
                "uptime": str(service.uptime),
                "running": service.is_running
            },
            "topics": 6,
            "subscribers": 2
        }
    service.check_health = AsyncMock(side_effect=mock_check_health)
    
    return service


class TestMessagingRouter:
    """Test messaging router endpoints."""

    def test_health_check(self, test_client, mock_messaging_service):
        """Test health check endpoint."""
        response = test_client.get("/messaging/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["topics"] == 4

    def test_health_check_error(self, test_client, mock_messaging_service):
        """Test health check with error."""
        mock_messaging_service.check_health.return_value = {
            "status": "error",
            "error": "Test error"
        }
        response = test_client.get("/messaging/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"] == "Test error"

    def test_get_topics(self, test_client, mock_messaging_service):
        """Test get topics endpoint."""
        response = test_client.get("/messaging/topics")
        assert response.status_code == 200
        data = response.json()
        assert len(data["topics"]) == 4

    def test_get_subscriber_count(self, test_client, mock_messaging_service):
        """Test get subscriber count endpoint."""
        response = test_client.get("/messaging/subscribers/test/topic")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_get_service_not_initialized(self):
        """Test get_service when not initialized."""
        # Reset service state
        import sys
        
        # Store original service
        original_service = sys.modules['micro_cold_spray.api.messaging.router']._service
        
        try:
            # Reset service to None
            sys.modules['micro_cold_spray.api.messaging.router']._service = None
            
            with pytest.raises(HTTPException) as exc:
                get_service()
            assert exc.value.status_code == 503
            assert exc.value.detail["error"] == "Service Unavailable"
            assert "not initialized" in exc.value.detail["message"]
        finally:
            # Restore service state
            sys.modules['micro_cold_spray.api.messaging.router']._service = original_service

    def test_validate_topic_empty(self, test_client):
        """Test topic validation with empty topic."""
        response = test_client.post("/messaging/publish/", json={"key": "value"})
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "Not Found"
        assert "Topic not found" in data["detail"]["message"]

        response = test_client.post("/messaging/publish/ ", json={"key": "value"})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "Invalid Action"
        assert "Invalid topic name" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_publish_message(self, async_client, mock_messaging_service):
        """Test publishing a message."""
        response = await async_client.post("/messaging/publish/test/topic", json={"key": "value"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["topic"] == "test/topic"
        mock_messaging_service.publish.assert_called_once_with("test/topic", {"key": "value"})

    @pytest.mark.asyncio
    async def test_request_message(self, async_client, mock_messaging_service):
        """Test request-response message."""
        test_response = {"response": "test"}
        mock_messaging_service.request.return_value = test_response
        
        response = await async_client.post("/messaging/request/test/topic", json={"key": "value"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["response"] == test_response
        mock_messaging_service.request.assert_called_once_with("test/topic", {"key": "value"})

    def test_websocket_subscribe(self, test_client, mock_messaging_service):
        """Test WebSocket subscription."""
        with test_client.websocket_connect("/messaging/subscribe/test/topic") as websocket:
            # Send subscribe message
            websocket.send_json({"type": "subscribe"})
            
            # Verify subscription acknowledgment
            response = websocket.receive_json()
            assert response["type"] == "subscribed"
            assert response["topic"] == "test/topic"
            assert "timestamp" in response
            
            # Send ping message
            websocket.send_json({"type": "ping"})
            
            # Verify pong response
            response = websocket.receive_json()
            assert response["type"] == "pong"
            
            # Verify subscription was created
            mock_messaging_service.subscribe.assert_called_once()

    def test_websocket_invalid_topic(self, test_client, mock_messaging_service):
        """Test WebSocket with invalid topic."""
        mock_messaging_service.subscribe.side_effect = MessageError(
            "Unknown topic",
            {"topic": "invalid/topic", "valid_topics": []}
        )
        
        with pytest.raises(WebSocketDisconnect) as exc:
            with test_client.websocket_connect("/messaging/subscribe/invalid/topic"):
                pass
        assert exc.value.code == 1008  # Policy violation

    @pytest.mark.asyncio
    async def test_service_control(self, async_client, mock_messaging_service):
        """Test service control endpoints."""
        # Test stop
        response = await async_client.post("/messaging/control", json={"action": "stop"})
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
        mock_messaging_service.stop.assert_called_once()

        # Test start
        response = await async_client.post("/messaging/control", json={"action": "start"})
        assert response.status_code == 200
        assert response.json()["status"] == "started"
        mock_messaging_service.start.assert_called_once()

        # Test restart
        response = await async_client.post("/messaging/control", json={"action": "restart"})
        assert response.status_code == 200
        assert response.json()["status"] == "restarted"
        assert mock_messaging_service.stop.call_count == 2
        assert mock_messaging_service.start.call_count == 2

    @pytest.mark.asyncio
    async def test_set_topics(self, async_client, mock_messaging_service):
        """Test setting valid topics."""
        new_topics = {"topic1", "topic2", "topic3"}
        
        response = await async_client.post("/messaging/topics", json=list(new_topics))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert len(data["topics"]) == len(new_topics)
        assert data["count"] == len(new_topics)
        mock_messaging_service.set_valid_topics.assert_called_once_with(new_topics)

    @pytest.mark.asyncio
    async def test_service_startup_failure(self, mocker):
        """Test service startup failure handling."""
        # Reset service state
        import sys
        
        # Store original service
        original_service = sys.modules['micro_cold_spray.api.messaging.router']._service
        
        try:
            # Reset service to None
            sys.modules['micro_cold_spray.api.messaging.router']._service = None
            
            # Mock config service to raise an error
            mock_get_config = mocker.patch(
                'micro_cold_spray.api.messaging.router.get_config_service',
                side_effect=Exception("Failed to get config service"))
            
            # Create a mock FastAPI app
            mock_app = mocker.MagicMock()
            
            # Test the lifespan context manager
            async with lifespan(mock_app):
                pytest.fail("Should not reach this point")  # Should raise before this
        except Exception as exc:
            assert "Failed to get config service" in str(exc)
            mock_get_config.assert_called_once()
        finally:
            # Restore service state
            sys.modules['micro_cold_spray.api.messaging.router']._service = original_service

    @pytest.mark.asyncio
    async def test_service_control_invalid_action(self, async_client):
        """Test service control with invalid action."""
        response = await async_client.post("/messaging/control", json={"action": "invalid"})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "Invalid Action"
        assert "Invalid action" in data["detail"]["message"]
        assert "valid_actions" in data["detail"]["data"]

    @pytest.mark.asyncio
    async def test_service_control_missing_action(self, async_client):
        """Test service control with missing action."""
        response = await async_client.post("/messaging/control", json={})
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "Missing Parameter"
        assert "Missing action" in data["detail"]["message"]
        assert "valid_actions" in data["detail"]["data"]

    @pytest.mark.asyncio
    async def test_startup_with_config(self, mocker):
        """Test startup with configuration."""
        mock_config = AsyncMock()
        mock_config.get_config.return_value = ConfigData(
            metadata=ConfigMetadata(
                config_type="application",
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={
                "services": {
                    "message_broker": {
                        "topics": {
                            "system": ["state", "health"],
                            "data": ["spray", "position"]
                        },
                        "max_subscribers": 5,
                        "timeout": 3.0
                    }
                }
            }
        )
        
        with patch("micro_cold_spray.api.messaging.router.get_config_service", return_value=mock_config):
            mock_app = mocker.MagicMock()
            async with lifespan(mock_app):
                mock_config.start.assert_called_once()
                assert mock_config.get_config.called
                assert mock_config.get_config.call_args[0][0] == "application"

    def test_service_configuration(self, mock_messaging_service, mock_config_service):
        """Test service configuration from config service."""
        assert mock_messaging_service._config_service == mock_config_service
        assert mock_messaging_service.is_initialized
        assert mock_messaging_service.is_running

    @pytest.mark.asyncio
    async def test_config_error_handling(self, mock_messaging_service, mock_config_service):
        """Test handling of configuration errors."""
        mock_config_service.get_config.side_effect = ConfigurationError("Config error")
        
        with pytest.raises(ConfigurationError, match="Config error"):
            await mock_messaging_service._start()

    def test_health_check_includes_config(self, test_client, mock_messaging_service):
        """Test health check includes configuration status."""
        response = test_client.get("/messaging/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "topics" in data
        assert data["topics"] == 6  # Total number of topics from mock config

    def test_topics_from_config(self, test_client, mock_messaging_service):
        """Test topics are loaded from configuration."""
        response = test_client.get("/messaging/topics")
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        topics = data["topics"]
        assert len(topics) == 6  # Total number of topics from mock config
        assert "state" in topics
        assert "spray" in topics
