"""Tests for state management router."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from micro_cold_spray.api.state.router import app, get_state_service, router
from micro_cold_spray.api.base.router import add_health_endpoints
from micro_cold_spray.api.state.models import StateRequest, StateResponse, StateTransition
from micro_cold_spray.api.state.exceptions import (
    StateError,
    StateTransitionError,
    InvalidStateError,
    ConditionError
)
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    service.is_running = True
    service.start_time = datetime.now()
    
    # Mock get_config to return proper config data
    async def mock_get_config(config_type: str):
        return ConfigData(
            metadata=ConfigMetadata(
                config_type=config_type,
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={
                "state_machine": {
                    "initial_state": "INIT",
                    "states": {
                        "INIT": {
                            "transitions": ["READY"],
                            "conditions": ["hardware.connected"]
                        },
                        "READY": {
                            "transitions": ["RUNNING", "ERROR"],
                            "conditions": ["hardware.enabled"]
                        }
                    }
                }
            }
        )
    service.get_config.side_effect = mock_get_config
    return service


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    broker = AsyncMock()
    broker.is_running = True
    broker.start = AsyncMock()
    broker.stop = AsyncMock()
    broker.set_valid_topics = AsyncMock()
    return broker


@pytest.fixture
def mock_communication_service():
    """Create mock communication service."""
    service = AsyncMock()
    service.is_running = True
    service.start = AsyncMock()
    service.stop = AsyncMock()
    return service


@pytest.fixture
def mock_state_service(mock_config_service, mock_message_broker, mock_communication_service):
    """Create mock state service."""
    service = AsyncMock()
    service.is_running = True
    service.start_time = datetime.now()
    service.uptime = 60
    service.current_state = "INIT"
    service.name = "state"
    service._config_service = mock_config_service
    service._message_broker = mock_message_broker
    service._communication_service = mock_communication_service
    
    # Configure mock responses
    service.transition_to.return_value = StateResponse(
        success=True,
        old_state="INIT",
        new_state="READY",
        timestamp=datetime.now()
    )
    
    service.get_state_history.return_value = [
        StateTransition(
            old_state="INIT",
            new_state="READY",
            timestamp=datetime.now(),
            reason="Test transition",
            conditions_met={"hardware.connected": True}
        )
    ]
    
    service.get_valid_transitions.return_value = {
        "INIT": ["READY"],
        "READY": ["RUNNING", "ERROR"]
    }
    
    service.check_health.return_value = {
        "status": "ok",
        "dependencies": {
            "config": {"status": "ok"},
            "messaging": {"status": "ok"},
            "communication": {"status": "ok"}
        },
        "details": {
            "current_state": "INIT",
            "states_configured": 4,
            "history_entries": 1
        }
    }
    
    service.get_conditions.return_value = {
        "hardware.connected": True,
        "hardware.enabled": True,
        "hardware.safe": True
    }
    
    return service


@pytest.fixture
def client(mock_state_service):
    """Create test client."""
    # Reset the app
    app.dependency_overrides = {}
    app.router.routes = []
    
    # Add dependencies and routes
    app.dependency_overrides[get_state_service] = lambda: mock_state_service
    app.include_router(router, prefix="/state")
    add_health_endpoints(app, mock_state_service)
    
    # Set state service in app state
    app.state._state_service = mock_state_service
    
    return TestClient(app)


class TestStateRouter:
    """Test state management router endpoints."""

    def test_get_status(self, client, mock_state_service):
        """Test status endpoint."""
        response = client.get("/state/status")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "INIT"
        assert "timestamp" in data

    def test_get_conditions(self, client, mock_state_service):
        """Test conditions endpoint."""
        response = client.get("/state/conditions")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "INIT"
        assert "conditions" in data

    def test_get_conditions_with_state(self, client, mock_state_service):
        """Test conditions endpoint with specific state."""
        response = client.get("/state/conditions?state=READY")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "READY"
        assert "conditions" in data

    def test_get_conditions_invalid_state(self, client, mock_state_service):
        """Test conditions endpoint with invalid state."""
        mock_state_service.get_conditions.side_effect = InvalidStateError("Invalid state")
        response = client.get("/state/conditions?state=INVALID")
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "Invalid State"
        assert response.json()["detail"]["message"] == "Invalid state"

    def test_transition_state(self, client, mock_state_service):
        """Test state transition endpoint."""
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "Test transition",
            "force": False
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["old_state"] == "INIT"
        assert data["new_state"] == "READY"

    def test_transition_invalid_state(self, client, mock_state_service):
        """Test transition to invalid state."""
        mock_state_service.transition_to.side_effect = InvalidStateError("Invalid state")
        response = client.post("/state/transition", json={
            "target_state": "INVALID",
            "reason": "Test transition"
        })
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "Invalid State"
        assert data["detail"]["message"] == "Invalid state"

    def test_transition_error(self, client, mock_state_service):
        """Test transition error handling."""
        mock_state_service.transition_to.side_effect = StateTransitionError("Transition failed")
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "Test transition"
        })
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error"] == "State Transition Error"
        assert data["detail"]["message"] == "Transition failed"

    def test_transition_condition_error(self, client, mock_state_service):
        """Test transition condition error handling."""
        mock_state_service.transition_to.side_effect = ConditionError(
            "Conditions not met",
            ["hardware.enabled"]
        )
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "Test transition"
        })
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "Condition Error"
        assert data["detail"]["message"] == "Conditions not met"
        assert "data" in data["detail"]
        assert "failed_conditions" in data["detail"]["data"]
        failed_conditions = data["detail"]["data"]["failed_conditions"]
        assert isinstance(failed_conditions, list)
        assert "hardware.enabled" in failed_conditions

    def test_get_history(self, client, mock_state_service):
        """Test history endpoint."""
        response = client.get("/state/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "old_state" in data[0]
        assert "new_state" in data[0]

    def test_get_history_with_limit(self, client, mock_state_service):
        """Test history endpoint with limit."""
        response = client.get("/state/history?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_get_transitions(self, client, mock_state_service):
        """Test transitions endpoint."""
        response = client.get("/state/transitions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "INIT" in data
        assert "READY" in data

    def test_service_not_initialized(self, client):
        """Test endpoints when service is not initialized."""
        app.dependency_overrides[get_state_service] = lambda: None
        response = client.get("/state/status")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "Service Unavailable"

    def test_health_check(self, client, mock_state_service):
        """Test health check endpoint."""
        mock_state_service.check_health.return_value = {
            "status": "ok",
            "details": {}
        }
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "process_info" in data

    def test_health_check_error(self, client, mock_state_service):
        """Test health check error handling."""
        mock_state_service.check_health.side_effect = Exception("Health check failed")
        response = client.get("/health")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Health Check Failed"
        assert data["detail"]["message"] == "Health check failed"

    def test_health_check_degraded(self, client, mock_state_service):
        """Test health check with degraded status."""
        mock_state_service.check_health.return_value = {
            "status": "degraded",
            "dependencies": {
                "config": {"status": "ok"},
                "messaging": {"status": "error", "error": "Connection failed"},
                "communication": {"status": "ok"}
            }
        }
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["messaging"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_startup_shutdown(self, mock_config_service, mock_message_broker, mock_communication_service):
        """Test startup and shutdown events."""
        from micro_cold_spray.api.state.router import _service
        
        with patch("micro_cold_spray.api.state.router.get_config_service", return_value=mock_config_service), \
             patch("micro_cold_spray.api.state.router.MessagingService", return_value=mock_message_broker), \
             patch("micro_cold_spray.api.state.router.CommunicationService", return_value=mock_communication_service):

            # Test startup
            await router.startup()
            mock_config_service.start.assert_called_once()
            mock_message_broker.start.assert_called_once()
            mock_communication_service.start.assert_called_once()
            mock_message_broker.set_valid_topics.assert_called_once()

            # Test shutdown
            await router.shutdown()
            assert _service is None

    def test_transition_invalid_request(self, client):
        """Test transition with invalid request body."""
        response = client.post("/state/transition", json={
            "invalid_field": "value"
        })
        assert response.status_code == 422  # Validation error

    def test_transition_missing_target(self, client):
        """Test transition with missing target state."""
        response = client.post("/state/transition", json={
            "reason": "Test transition"
        })
        assert response.status_code == 422

    def test_transition_empty_target(self, client):
        """Test transition with empty target state."""
        response = client.post("/state/transition", json={
            "target_state": "",
            "reason": "Test transition"
        })
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "Validation Error"

    def test_transition_state_error(self, client, mock_state_service):
        """Test generic state error handling."""
        mock_state_service.transition_to.side_effect = StateError("Generic state error")
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "Test transition"
        })
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Internal Server Error"
        assert data["detail"]["message"] == "Generic state error"

    def test_transition_unexpected_error(self, client, mock_state_service):
        """Test unexpected error handling in transition."""
        mock_state_service.transition_to.side_effect = Exception("Unexpected error")
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "Test transition"
        })
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Internal Server Error"
        assert data["detail"]["message"] == "Unexpected error"

    def test_get_conditions_state_error(self, client, mock_state_service):
        """Test state error in conditions endpoint."""
        mock_state_service.get_conditions.side_effect = StateError("State error")
        response = client.get("/state/conditions")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Internal Server Error"
        assert data["detail"]["message"] == "State error"

    def test_get_conditions_unexpected_error(self, client, mock_state_service):
        """Test unexpected error in conditions endpoint."""
        mock_state_service.get_conditions.side_effect = Exception("Unexpected error")
        response = client.get("/state/conditions")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Internal Server Error"
        assert data["detail"]["message"] == "Unexpected error"

    def test_get_history_error(self, client, mock_state_service):
        """Test error handling in history endpoint."""
        mock_state_service.get_state_history.side_effect = Exception("History error")
        response = client.get("/state/history")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Internal Server Error"
        assert data["detail"]["message"] == "History error"

    def test_get_transitions_error(self, client, mock_state_service):
        """Test error handling in transitions endpoint."""
        mock_state_service.get_valid_transitions.side_effect = Exception("Transitions error")
        response = client.get("/state/transitions")
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "Internal Server Error"
        assert data["detail"]["message"] == "Transitions error"

    @pytest.mark.asyncio
    async def test_startup_service_error(self, mock_config_service, mock_message_broker, mock_communication_service):
        """Test startup error handling."""
        mock_config_service.start.side_effect = Exception("Config service failed")
        
        with patch("micro_cold_spray.api.state.router.get_config_service", return_value=mock_config_service), \
             patch("micro_cold_spray.api.state.router.MessagingService", return_value=mock_message_broker), \
             patch("micro_cold_spray.api.state.router.CommunicationService", return_value=mock_communication_service):
            
            with pytest.raises(Exception, match="Config service failed"):
                await router.startup()

    @pytest.mark.asyncio
    async def test_shutdown_error(self, client, mock_state_service):
        """Test shutdown error handling."""
        mock_state_service.stop.side_effect = Exception("Stop error")
        with patch("micro_cold_spray.api.state.router._service", mock_state_service):
            await router.shutdown()
            # Should log error but not raise

    def test_transition_with_force(self, client, mock_state_service):
        """Test forced state transition."""
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "Forced transition",
            "force": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_state_service.transition_to.assert_awaited_with(
            StateRequest(target_state="READY", reason="Forced transition", force=True)
        )

    def test_get_history_invalid_limit(self, client):
        """Test history endpoint with invalid limit."""
        response = client.get("/state/history?limit=-1")
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("greater than or equal to 0" in error["msg"].lower() for error in data["detail"])

    def test_get_history_string_limit(self, client):
        """Test history endpoint with non-integer limit."""
        response = client.get("/state/history?limit=abc")
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert isinstance(data["detail"], list)
        error = data["detail"][0]
        assert error["loc"] == ["query", "limit"]
        assert error["msg"] == "Input should be a valid integer, unable to parse string as an integer"
        assert error["type"] == "int_parsing"

    def test_get_conditions_empty_state(self, client):
        """Test conditions endpoint with empty state parameter."""
        response = client.get("/state/conditions?state=")
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "Validation Error"
        assert "state" in data["detail"]["message"].lower()

    def test_transition_with_long_reason(self, client):
        """Test transition with very long reason text."""
        response = client.post("/state/transition", json={
            "target_state": "READY",
            "reason": "x" * 1000  # Very long reason
        })
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "Validation Error"
        assert "reason" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_startup_messaging_error(self, mock_config_service, mock_message_broker, mock_communication_service):
        """Test startup with messaging service error."""
        mock_message_broker.start.side_effect = Exception("Messaging service failed")
        
        with patch("micro_cold_spray.api.state.router.get_config_service", return_value=mock_config_service), \
             patch("micro_cold_spray.api.state.router.MessagingService", return_value=mock_message_broker), \
             patch("micro_cold_spray.api.state.router.CommunicationService", return_value=mock_communication_service):
            
            with pytest.raises(Exception, match="Messaging service failed"):
                await router.startup()

    @pytest.mark.asyncio
    async def test_startup_communication_error(self, mock_config_service, mock_message_broker, mock_communication_service):
        """Test startup with communication service error."""
        mock_communication_service.start.side_effect = Exception("Communication service failed")
        
        with patch("micro_cold_spray.api.state.router.get_config_service", return_value=mock_config_service), \
             patch("micro_cold_spray.api.state.router.MessagingService", return_value=mock_message_broker), \
             patch("micro_cold_spray.api.state.router.CommunicationService", return_value=mock_communication_service):
            
            with pytest.raises(Exception, match="Communication service failed"):
                await router.startup()

    @pytest.mark.asyncio
    async def test_startup_with_config(self, mock_config_service, mock_message_broker, mock_communication_service):
        """Test startup with configuration loading."""
        with patch("micro_cold_spray.api.state.router.get_config_service", return_value=mock_config_service), \
             patch("micro_cold_spray.api.state.router.MessagingService", return_value=mock_message_broker), \
             patch("micro_cold_spray.api.state.router.CommunicationService", return_value=mock_communication_service):
            
            mock_app = MagicMock()
            async with app.router.lifespan(mock_app):
                # Verify config was loaded
                mock_config_service.start.assert_called_once()
                mock_config_service.get_config.assert_called_with("state")
                assert mock_config_service.get_config.call_count >= 1

    def test_service_configuration(self, mock_state_service, mock_config_service):
        """Test service configuration from config service."""
        assert mock_state_service._config_service == mock_config_service
        assert mock_state_service.is_running is True
        assert mock_state_service.current_state == "INIT"

    def test_service_dependencies(self, mock_state_service, mock_message_broker, mock_communication_service):
        """Test service dependencies are properly initialized."""
        assert mock_state_service._message_broker == mock_message_broker
        assert mock_state_service._communication_service == mock_communication_service
        assert mock_message_broker.is_running is True
        assert mock_communication_service.is_running is True

    @pytest.mark.asyncio
    async def test_config_error_handling(self, mock_state_service, mock_config_service):
        """Test handling of configuration errors."""
        mock_config_service.get_config.side_effect = Exception("Config error")
        
        with pytest.raises(Exception, match="Config error"):
            await mock_state_service._start()

    def test_health_check_includes_config(self, client, mock_state_service):
        """Test health check includes config service status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "config" in data["dependencies"]
        assert data["dependencies"]["config"]["status"] == "ok"
