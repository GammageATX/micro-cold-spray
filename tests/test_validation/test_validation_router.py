"""Tests for validation router."""

import pytest
from unittest.mock import AsyncMock, PropertyMock
from fastapi.testclient import TestClient

from micro_cold_spray.api.validation.router import (
    app,
    init_router,
    get_service,
    ValidationService
)
from micro_cold_spray.api.base.exceptions import ValidationError
from micro_cold_spray.api.base.errors import ErrorCode


@pytest.fixture
def mock_validation_service():
    """Create mock validation service."""
    service = AsyncMock(spec=ValidationService)
    # Mock is_running as a property
    type(service).is_running = PropertyMock(return_value=True)
    return service


@pytest.fixture
def test_client(mock_validation_service):
    """Create test client with mock service."""
    # Initialize router with mock service
    init_router(mock_validation_service)
    # Include router in app
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
        
        response = test_client.post("/validate", json={
            "type": "parameters",
            "data": {"speed": 100}
        })
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        assert "timestamp" in response.json()

    async def test_validate_data_missing_type(self, test_client):
        """Test validation with missing type."""
        response = test_client.post("/validate", json={
            "data": {"speed": 100}
        })
        
        assert response.status_code == ErrorCode.MISSING_PARAMETER.get_status_code()
        assert response.json()["code"] == "MISSING_PARAMETER"
        assert "Missing validation type" in response.json()["message"]

    async def test_validate_data_missing_data(self, test_client):
        """Test validation with missing data."""
        response = test_client.post("/validate", json={
            "type": "parameters"
        })
        
        assert response.status_code == ErrorCode.MISSING_PARAMETER.get_status_code()
        assert response.json()["code"] == "MISSING_PARAMETER"
        assert "Missing validation data" in response.json()["message"]

    async def test_validate_data_unknown_type(self, test_client):
        """Test validation with unknown type."""
        response = test_client.post("/validate", json={
            "type": "unknown",
            "data": {}
        })
        
        assert response.status_code == ErrorCode.INVALID_ACTION.get_status_code()
        assert response.json()["code"] == "INVALID_ACTION"
        assert "Unknown validation type" in response.json()["message"]

    async def test_validate_data_validation_error(self, test_client, mock_validation_service):
        """Test validation with validation error."""
        mock_validation_service.validate_parameters.side_effect = ValidationError(
            "Validation failed",
            {"field": "speed"}
        )
        
        response = test_client.post("/validate", json={
            "type": "parameters",
            "data": {"speed": -1}
        })
        
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert "Validation failed" in response.json()["message"]

    async def test_validate_data_internal_error(self, test_client, mock_validation_service):
        """Test validation with internal error."""
        mock_validation_service.validate_parameters.side_effect = Exception("Internal error")
        
        response = test_client.post("/validate", json={
            "type": "parameters",
            "data": {"speed": 100}
        })
        
        assert response.status_code == ErrorCode.INTERNAL_ERROR.get_status_code()
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert "Internal error" in response.json()["message"]

    async def test_get_validation_rules_success(self, test_client, mock_validation_service):
        """Test successful rules retrieval."""
        mock_rules = {
            "required_fields": ["speed", "pressure"],
            "bounds": {"speed": [0, 100]}
        }
        mock_validation_service.get_rules.return_value = mock_rules
        
        response = test_client.get("/rules/parameters")
        
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
        
        response = test_client.get("/rules/unknown")
        
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        assert response.json()["code"] == "VALIDATION_ERROR"
        assert "Unknown rule type" in response.json()["message"]

    async def test_health_check_success(self, test_client, mock_validation_service):
        """Test successful health check."""
        type(mock_validation_service).is_running = PropertyMock(return_value=True)
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["service"] == "ok"
        assert "timestamp" in response.json()

    async def test_health_check_service_down(self, test_client, mock_validation_service):
        """Test health check when service is down."""
        type(mock_validation_service).is_running = PropertyMock(return_value=False)
        
        response = test_client.get("/health")
        
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        assert response.json()["code"] == "SERVICE_UNAVAILABLE"
        assert "Service not running" in response.json()["message"]

    async def test_health_check_error(self, test_client, mock_validation_service):
        """Test health check with error."""
        type(mock_validation_service).is_running = PropertyMock(side_effect=Exception("Health check failed"))
        
        response = test_client.get("/health")
        
        assert response.status_code == ErrorCode.HEALTH_CHECK_ERROR.get_status_code()
        assert response.json()["code"] == "HEALTH_CHECK_ERROR"
        assert "Health check failed" in response.json()["message"]
