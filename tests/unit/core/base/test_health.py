"""Tests for health check endpoints."""

import pytest
from fastapi import status
from tests.base import BaseAPITest, BaseServiceTest
from micro_cold_spray.core.errors.exceptions import ServiceError, ConfigurationError


@pytest.mark.unit
@pytest.mark.api
class TestHealthEndpoints(BaseAPITest):
    """Test cases for health check endpoints."""

    def test_get_health(self, mock_base_service):
        """Test getting health status."""
        mock_base_service.check_health.return_value = {
            "status": "ok",
            "service_info": {
                "name": "test_service",
                "version": "1.0.0",
                "running": True,
                "uptime": 0.0
            }
        }
        response = self.client.get("/health")
        self.assert_health_check(response)
    
    def test_health_error(self, mock_base_service):
        """Test health check with error."""
        mock_base_service.check_health.side_effect = ServiceError("Service error")
        response = self.client.get("/health")
        self.assert_error_response(response, status.HTTP_503_SERVICE_UNAVAILABLE, "Service error")
    
    def test_health_degraded(self, mock_base_service):
        """Test health check with degraded status."""
        mock_base_service.check_health.return_value = {
            "status": "degraded",
            "message": "Performance degraded",
            "service_info": {
                "name": "test_service",
                "version": "1.0.0",
                "running": True,
                "uptime": 0.0
            }
        }
        response = self.client.get("/health")
        self.assert_health_check(response)
        data = response.json()
        assert data["status"] == "degraded"
        assert data["message"] == "Performance degraded"
    
    def test_health_not_running(self, mock_base_service):
        """Test health check when service is not running."""
        mock_base_service.is_running = False
        mock_base_service.check_health.return_value = {
            "status": "stopped",
            "service_info": {
                "name": "test_service",
                "version": "1.0.0",
                "running": False,
                "uptime": None
            }
        }
        response = self.client.get("/health")
        self.assert_health_check(response)
        data = response.json()
        assert data["status"] == "stopped"
        assert not data["service_info"]["running"]
    
    def test_health_config_error(self, mock_base_service):
        """Test health check with configuration error."""
        mock_base_service.check_health.side_effect = ConfigurationError("Config error")
        response = self.client.get("/health")
        self.assert_error_response(response, status.HTTP_503_SERVICE_UNAVAILABLE, "Config error")
    
    @pytest.mark.asyncio
    async def test_health_async(self, mock_base_service):
        """Test async health check endpoint."""
        mock_base_service.check_health.return_value = {
            "status": "ok",
            "service_info": {
                "name": "test_service",
                "version": "1.0.0",
                "running": True,
                "uptime": 0.0
            }
        }
        response = await self.async_client.get("/health")
        await self.assert_async_success_response(response)
        data = await response.json()
        assert data["status"] == "ok"
        assert data["service_info"]["running"]


@pytest.mark.unit
@pytest.mark.service
class TestServiceHealthChecks(BaseServiceTest):
    """Test cases for individual service health checks."""
    
    def test_ui_health(self, ui_client):
        """Test UI service health check."""
        response = ui_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ui"
        assert "version" in data

    def test_config_health(self, config_client):
        """Test Config service health check."""
        response = config_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "is_production" in data

    def test_communication_health(self, communication_client):
        """Test Communication service health check."""
        response = communication_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "communication"
        assert "version" in data
        assert data["is_running"] is True

    def test_process_health(self, process_client):
        """Test Process service health check."""
        response = process_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "process"
        assert "version" in data
        assert data["is_running"] is True

    def test_state_health(self, state_client):
        """Test State service health check."""
        response = state_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "state"
        assert "version" in data
        assert data["is_running"] is True

    def test_data_collection_health(self, data_collection_client):
        """Test Data Collection service health check."""
        response = data_collection_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "data_collection"
        assert "version" in data
        assert data["is_running"] is True

    def test_validation_health(self, validation_client):
        """Test Validation service health check."""
        response = validation_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "validation"
        assert "version" in data
        assert data["is_running"] is True

    def test_messaging_health(self, messaging_client):
        """Test Messaging service health check."""
        response = messaging_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "messaging"
        assert "version" in data
        assert data["is_running"] is True

    @pytest.mark.parametrize("client_fixture,service_name", [
        ("ui_client", "ui"),
        ("config_client", "config"),
        ("communication_client", "communication"),
        ("process_client", "process"),
        ("state_client", "state"),
        ("data_collection_client", "data_collection"),
        ("validation_client", "validation"),
        ("messaging_client", "messaging")
    ])
    def test_all_services_health(self, request, client_fixture, service_name):
        """Test health checks for all services in a single test."""
        client = request.getfixturevalue(client_fixture)
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["healthy", "ok"]  # Different services use different status strings
        if "service_name" in data:
            assert data["service_name"] == service_name
        elif "service" in data:
            assert data["service"] == service_name
        assert "version" in data
