"""Integration tests for health check endpoints."""
import pytest
from fastapi import status


class TestHealthChecks:
    """Test cases for health check endpoints."""

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
