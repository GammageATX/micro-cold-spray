"""Tests for validation router."""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from micro_cold_spray.api.validation.router import (
    app,
    init_router,
    get_service,
    ValidationService
)
from micro_cold_spray.api.validation.exceptions import ValidationError


@pytest.fixture
def mock_validation_service():
    """Create mock validation service."""
    service = AsyncMock(spec=ValidationService)
    service.is_running = True
    return service


@pytest.fixture
def test_client(mock_validation_service):
    """Create test client with mock service."""
    init_router(mock_validation_service)
    return TestClient(app)


class TestValidationRouter:
    """Test validation router functionality."""

    def test_get_service_not_initialized(self):
        """Test get_service when not initialized."""
        with pytest.raises(Exception) as exc_info:
            get_service()
        assert "Validation service not initialized" in str(exc_info.value)

    def test_get_service_initialized(self, mock_validation_service):
        """Test get_service when initialized."""
        init_router(mock_validation_service)
        service = get_service()
        assert service == mock_validation_service

    async def test_validate_data_success(self, test_client, mock_validation_service):
        """Test successful data validation."""
        mock_validation_service.validate_parameters.return_value = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        response = test_client.post("/validation/validate", json={
            "type": "parameters",
            "data": {"speed": 100}
        })
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        assert "timestamp" in response.json()

    async def test_validate_data_missing_type(self, test_client):
        """Test validation with missing type."""
        response = test_client.post("/validation/validate", json={
            "data": {"speed": 100}
        })
        
        assert response.status_code == 400
        assert "Missing validation type" in response.json()["detail"]["message"]

    async def test_validate_data_missing_data(self, test_client):
        """Test validation with missing data."""
        response = test_client.post("/validation/validate", json={
            "type": "parameters"
        })
        
        assert response.status_code == 400
        assert "Missing validation data" in response.json()["detail"]["message"]

    async def test_validate_data_unknown_type(self, test_client):
        """Test validation with unknown type."""
        response = test_client.post("/validation/validate", json={
            "type": "unknown",
            "data": {}
        })
        
        assert response.status_code == 400
        assert "Unknown validation type" in response.json()["detail"]["message"]

    async def test_validate_data_validation_error(self, test_client, mock_validation_service):
        """Test validation with validation error."""
        mock_validation_service.validate_parameters.side_effect = ValidationError(
            "Validation failed",
            {"field": "speed"}
        )
        
        response = test_client.post("/validation/validate", json={
            "type": "parameters",
            "data": {"speed": -1}
        })
        
        assert response.status_code == 400
        assert "Validation failed" in response.json()["detail"]["message"]

    async def test_validate_data_internal_error(self, test_client, mock_validation_service):
        """Test validation with internal error."""
        mock_validation_service.validate_parameters.side_effect = Exception("Internal error")
        
        response = test_client.post("/validation/validate", json={
            "type": "parameters",
            "data": {"speed": 100}
        })
        
        assert response.status_code == 500
        assert "Internal error" in response.json()["detail"]["message"]

    async def test_get_validation_rules_success(self, test_client, mock_validation_service):
        """Test successful rules retrieval."""
        mock_rules = {
            "required_fields": ["speed", "pressure"],
            "bounds": {"speed": [0, 100]}
        }
        mock_validation_service.get_rules.return_value = mock_rules
        
        response = test_client.get("/validation/rules/parameters")
        
        assert response.status_code == 200
        assert response.json()["type"] == "parameters"
        assert response.json()["rules"] == mock_rules
        assert "timestamp" in response.json()

    async def test_get_validation_rules_not_found(self, test_client, mock_validation_service):
        """Test rules retrieval for unknown type."""
        mock_validation_service.get_rules.side_effect = ValidationError(
            "Unknown rule type",
            {"type": "unknown"}
        )
        
        response = test_client.get("/validation/rules/unknown")
        
        assert response.status_code == 400
        assert "Unknown rule type" in response.json()["detail"]["message"]

    async def test_health_check_success(self, test_client, mock_validation_service):
        """Test successful health check."""
        mock_validation_service.is_running = True
        
        response = test_client.get("/validation/health")
        
        assert response.status_code == 200
        assert response.json()["service"] == "ok"
        assert "timestamp" in response.json()

    async def test_health_check_service_down(self, test_client, mock_validation_service):
        """Test health check when service is down."""
        mock_validation_service.is_running = False
        
        response = test_client.get("/validation/health")
        
        assert response.status_code == 503
        assert "Service not running" in response.json()["detail"]["message"]

    async def test_health_check_error(self, test_client, mock_validation_service):
        """Test health check with error."""
        mock_validation_service.is_running.side_effect = Exception("Health check failed")
        
        response = test_client.get("/validation/health")
        
        assert response.status_code == 500
        assert "Health check failed" in response.json()["detail"]["message"]
