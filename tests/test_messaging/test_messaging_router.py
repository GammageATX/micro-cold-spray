"""Tests for messaging router."""

import pytest
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect
from micro_cold_spray.api.messaging.router import get_service, lifespan
from micro_cold_spray.api.base.exceptions import MessageError


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
