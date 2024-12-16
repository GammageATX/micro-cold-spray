"""Tests for messaging router."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from starlette.websockets import WebSocketDisconnect

from micro_cold_spray.api.messaging.router import router, startup, shutdown, get_service
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.base.exceptions import MessageError


class TestMessagingRouter:
    """Test messaging router endpoints."""

    @pytest.fixture
    def mock_messaging_service(self):
        """Create mock messaging service."""
        mock = AsyncMock()
        mock.check_health.return_value = {
            "status": "ok",
            "topics": 4,
            "active_subscribers": 2,
            "background_tasks": 1,
            "queue_size": 0
        }
        mock.get_topics.return_value = {"test/topic", "test/response", "control/start", "control/stop"}
        mock.get_subscriber_count.return_value = 2
        mock.publish = AsyncMock()
        mock.subscribe = AsyncMock()
        mock.request = AsyncMock(return_value={"response": "test"})
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.set_valid_topics = AsyncMock()
        return mock

    @pytest.fixture
    def mock_config_service(self):
        """Create mock config service."""
        mock = AsyncMock(spec=ConfigService)
        mock.get_config.return_value = AsyncMock(
            data={
                "services": {
                    "message_broker": {
                        "topics": {
                            "test": ["test/topic", "test/response"],
                            "control": ["control/start", "control/stop"]
                        }
                    }
                }
            }
        )
        return mock

    @pytest.fixture
    async def app(self, mock_messaging_service, mock_config_service):
        """Create FastAPI app for testing."""
        app = FastAPI()
        app.include_router(router)
        
        # Initialize services
        with patch('micro_cold_spray.api.messaging.router._service', mock_messaging_service), \
             patch('micro_cold_spray.api.messaging.router.get_config_service', return_value=mock_config_service):
            await startup()
            yield app
            await shutdown()

    @pytest.fixture
    def test_client(self, app):
        """Create test client with mock service."""
        with TestClient(app) as client:
            yield client

    @pytest.fixture
    async def async_client(self, app):
        """Create async client for testing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

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
        with patch('micro_cold_spray.api.messaging.router._service', None):
            with pytest.raises(RuntimeError, match="Messaging service not initialized"):
                get_service()

    def test_validate_topic_empty(self, test_client):
        """Test topic validation with empty topic."""
        response = test_client.post("/messaging/publish/", json={"key": "value"})
        assert response.status_code == 404

        response = test_client.post("/messaging/publish/ ", json={"key": "value"})
        assert response.status_code == 400
        assert "Invalid topic name" in response.json()["detail"]["error"]

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
        
        with pytest.raises(WebSocketDisconnect):
            with test_client.websocket_connect("/messaging/subscribe/invalid/topic"):
                pass

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
    async def test_service_startup_failure(self):
        """Test service startup failure handling."""
        with patch('micro_cold_spray.api.messaging.router.get_config_service') as mock_get_config:
            mock_config = AsyncMock(spec=ConfigService)
            mock_config.start.side_effect = Exception("Startup failed")
            mock_get_config.return_value = mock_config
            
            with pytest.raises(Exception, match="Startup failed"):
                await startup()

    @pytest.mark.asyncio
    async def test_service_control_invalid_action(self, async_client):
        """Test service control with invalid action."""
        response = await async_client.post("/messaging/control", json={"action": "invalid"})
        assert response.status_code == 400
        data = response.json()
        assert "Invalid action" in data["detail"]["error"]
        assert "valid_actions" in data["detail"]

    @pytest.mark.asyncio
    async def test_service_control_missing_action(self, async_client):
        """Test service control with missing action."""
        response = await async_client.post("/messaging/control", json={})
        assert response.status_code == 400
        data = response.json()
        assert "Missing action" in data["detail"]["error"]
        assert "valid_actions" in data["detail"]
