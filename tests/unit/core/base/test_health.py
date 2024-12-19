"""Tests for health check endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi import status
from .test_base import BaseAPITest

class TestHealthEndpoints(BaseAPITest):
    """Test cases for health check endpoints."""

    def test_get_health(self):
        """Test getting health status."""
        response = self.client.get("/health")
        self.assert_health_check(response)
    
    def test_get_health_details(self):
        """Test getting detailed health status."""
        response = self.client.get("/health/details")
        self.assert_success_response(response)
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "version" in data
        assert "uptime" in data
        assert "services" in data
        
        # Validate services data
        services = data["services"]
        assert isinstance(services, dict)
        for service_name, service_data in services.items():
            assert "status" in service_data
            assert "version" in service_data
            assert "uptime" in service_data
    
    @pytest.mark.asyncio
    async def test_async_health_check(self):
        """Test async health check endpoint."""
        response = await self.async_client.get("/health")
        await self.assert_async_success_response(response)
        data = await response.json()
        
        assert data["status"] == "ok"
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] >= 0
    
    def test_health_service_down(self, mock_base_service):
        """Test health check when service is down."""
        # Simulate service being down
        mock_base_service.is_running = False
        mock_base_service.check_health.return_value = {"status": "error", "message": "Service is down"}
        
        response = self.client.get("/health")
        self.assert_error_response(response, status_code=503)
        data = response.json()
        assert data["status"] == "error"
        assert "message" in data
    
    def test_health_uptime_calculation(self, mock_base_service):
        """Test uptime calculation in health check."""
        # Set a specific start time
        start_time = datetime.now() - timedelta(hours=1)
        mock_base_service.start_time = start_time
        
        response = self.client.get("/health")
        self.assert_success_response(response)
        data = response.json()
        
        # Uptime should be approximately 1 hour (3600 seconds)
        assert abs(data["uptime"] - 3600) < 10  # Allow 10 seconds tolerance

class TestServiceHealthChecks:
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