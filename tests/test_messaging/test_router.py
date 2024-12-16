"""Tests for messaging router."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.api.messaging.router import router, startup, shutdown
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
        return mock

    @pytest.fixture
    async def test_client(self, mock_messaging_service):
        """Create test client with mock service."""
        # Create FastAPI app
        app = FastAPI()
        
        # Include router before patching service
        app.include_router(router)
        
        # Mock the service singleton
        with patch('micro_cold_spray.api.messaging.router._service', mock_messaging_service):
            # Initialize service before creating client
            await startup()
            
            # Create test client
            client = TestClient(app)
            
            yield client
            
            # Cleanup
            await shutdown()

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

    def test_get_topics_error(self, test_client, mock_messaging_service):
        """Test get topics with error."""
        mock_messaging_service.get_topics.side_effect = Exception("Test error")
        response = test_client.get("/messaging/topics")
        assert response.status_code == 500

    def test_get_subscriber_count(self, test_client, mock_messaging_service):
        """Test get subscriber count endpoint."""
        response = test_client.get("/messaging/subscribers/test/topic")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_get_subscriber_count_error(self, test_client, mock_messaging_service):
        """Test get subscriber count with error."""
        mock_messaging_service.get_subscriber_count.side_effect = Exception("Test error")
        response = test_client.get("/messaging/subscribers/test/topic")
        assert response.status_code == 500

    def test_publish_message(self, test_client, mock_messaging_service):
        """Test publish message endpoint."""
        test_data = {"key": "value"}
        response = test_client.post(
            "/messaging/publish/test/topic",
            json=test_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["topic"] == "test/topic"

    def test_publish_message_error(self, test_client, mock_messaging_service):
        """Test publish message with error."""
        mock_messaging_service.publish.side_effect = Exception("Test error")
        response = test_client.post(
            "/messaging/publish/test/topic",
            json={"key": "value"}
        )
        assert response.status_code == 500

    def test_request_message(self, test_client, mock_messaging_service):
        """Test request message endpoint."""
        request_data = {"key": "value"}
        mock_messaging_service.request.return_value = {"response": "test"}
        
        response = test_client.post(
            "/messaging/request/test/topic",
            json=request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "test/topic"
        assert data["response"] == {"response": "test"}

    def test_request_message_error(self, test_client, mock_messaging_service):
        """Test request message with error."""
        mock_messaging_service.request.side_effect = Exception("Test error")
        response = test_client.post(
            "/messaging/request/test/topic",
            json={"key": "value"}
        )
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_startup_shutdown(self):
        """Test router startup and shutdown events."""
        with patch('micro_cold_spray.api.messaging.router.get_config_service') as mock_get_config:
            mock_config = AsyncMock(spec=ConfigService)
            mock_get_config.return_value = mock_config
            
            # Test startup
            await startup()
            mock_config.start.assert_called_once()
            
            # Test shutdown
            await shutdown()
            mock_config.stop.assert_called_once()
