"""Tests for configuration router.

This module contains tests for the configuration API router endpoints.
Tests cover CRUD operations, validation, error handling, and health checks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Dict, Any, Generator

from micro_cold_spray.api.config.router import router, init_router, get_service
from micro_cold_spray.api.config.models import (
    ConfigValidationResult,
    ConfigData,
    ConfigMetadata
)
from micro_cold_spray.api.base.exceptions import ConfigurationError


@pytest.fixture
def mock_config_service() -> MagicMock:
    """Create mock config service with pre-configured async methods.
    
    Returns:
        MagicMock: Configured mock service instance
    """
    service = MagicMock()
    service.is_running = True
    service._service_name = "config"
    service.version = "1.0.0"
    service.check_health = AsyncMock(return_value={
        "status": "ok",
        "service_info": {
            "version": "1.0.0",
            "running": True
        }
    })
    service.get_config = AsyncMock()
    service.update_config = AsyncMock()
    service.validate_config = AsyncMock()
    service.clear_cache = AsyncMock()
    service.start = AsyncMock()
    service.stop = AsyncMock()
    service.get_config_types = AsyncMock()
    return service


@pytest.fixture
def test_client(mock_config_service) -> Generator[TestClient, None, None]:
    """Create a test client with mock service.
    
    Args:
        mock_config_service: Mock service instance
        
    Returns:
        TestClient: Configured FastAPI test client
    """
    init_router(mock_config_service)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: mock_config_service
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_config_data() -> Dict[str, Any]:
    """Sample configuration data for testing.
    
    Returns:
        Dict[str, Any]: Sample configuration data
    """
    return {
        "name": "test_config",
        "version": "1.0.0",
        "settings": {
            "param1": "value1",
            "param2": 42
        }
    }


class TestConfigTypes:
    """Tests for configuration type endpoints."""
    
    def test_get_types_success(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test getting available config types successfully."""
        expected_types = [
            {"id": "application", "name": "Application"},
            {"id": "hardware", "name": "Hardware"}
        ]
        mock_config_service.get_config_types.return_value = expected_types
        
        response = test_client.get("/api/config/types")
        assert response.status_code == 200
        data = response.json()
        assert data == {"types": expected_types}
        mock_config_service.get_config_types.assert_called_once()
    
    def test_get_types_error(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test getting config types with service error."""
        mock_config_service.get_config_types.side_effect = ConfigurationError("Service error")
        
        response = test_client.get("/api/config/types")
        assert response.status_code == 400
        assert response.json()["detail"] == "Service error"


class TestHealthCheck:
    """Tests for health check endpoints."""
    
    def test_success(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test successful health check."""
        response = test_client.get("/api/config/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "status": "ok",
            "service_name": "config",
            "version": "1.0.0",
            "is_running": True
        }
    
    @pytest.mark.parametrize("is_running,expected_status", [
        (False, 503),
        (True, 200)
    ])
    def test_status(
        self,
        test_client: TestClient,
        mock_config_service: MagicMock,
        is_running: bool,
        expected_status: int
    ):
        """Test health check with different service states."""
        mock_config_service.is_running = is_running
        mock_config_service.check_health.return_value = {
            "status": "ok" if is_running else "error",
            "service_info": {
                "version": "1.0.0",
                "running": is_running
            }
        }
        
        response = test_client.get("/api/config/health")
        assert response.status_code == expected_status


class TestConfigOperations:
    """Tests for configuration CRUD operations."""
    
    def test_get_success(
        self,
        test_client: TestClient,
        mock_config_service: MagicMock,
        sample_config_data: Dict[str, Any]
    ):
        """Test getting configuration successfully."""
        timestamp = datetime.now()
        mock_config_service.get_config.return_value = ConfigData(
            metadata=ConfigMetadata(
                config_type="test",
                last_modified=timestamp,
                version="1.0.0"
            ),
            data=sample_config_data
        )
        
        response = test_client.get("/api/config/test")
        assert response.status_code == 200
        data = response.json()
        assert data["config"] == sample_config_data
        assert "timestamp" in data
        mock_config_service.get_config.assert_called_once_with("test")
    
    def test_get_not_found(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test getting non-existent configuration."""
        mock_config_service.get_config.side_effect = ConfigurationError("Config not found")
        
        response = test_client.get("/api/config/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Config not found"
    
    def test_update_success(
        self,
        test_client: TestClient,
        mock_config_service: MagicMock,
        sample_config_data: Dict[str, Any]
    ):
        """Test updating configuration successfully."""
        mock_config_service.update_config.return_value = ConfigValidationResult(
            valid=True,
            errors=[],
            warnings=[]
        )
        
        response = test_client.post("/api/config/test", json=sample_config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["validation"]["valid"] is True
        mock_config_service.update_config.assert_called_once_with("test", sample_config_data)
    
    def test_update_validation_error(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test updating configuration with validation error."""
        error_msg = "Invalid configuration"
        mock_config_service.update_config.side_effect = ConfigurationError(
            error_msg,
            {"field": "settings"}
        )
        
        response = test_client.post("/api/config/test", json={"invalid": "data"})
        assert response.status_code == 422
        assert response.json()["detail"] == error_msg


class TestValidation:
    """Tests for configuration validation."""
    
    def test_success(
        self,
        test_client: TestClient,
        mock_config_service: MagicMock,
        sample_config_data: Dict[str, Any]
    ):
        """Test validating configuration successfully."""
        expected_result = ConfigValidationResult(
            valid=True,
            errors=[],
            warnings=["Optional field missing"]
        )
        mock_config_service.validate_config.return_value = expected_result
        
        response = test_client.post("/api/config/test/validate", json=sample_config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) == 1
        mock_config_service.validate_config.assert_called_once_with("test", sample_config_data)
    
    def test_invalid(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test validating invalid configuration."""
        mock_config_service.validate_config.return_value = ConfigValidationResult(
            valid=False,
            errors=["Required field missing"],
            warnings=[]
        )
        
        response = test_client.post("/api/config/test/validate", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 1


class TestCache:
    """Tests for cache operations."""
    
    def test_clear_success(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test clearing cache successfully."""
        response = test_client.post("/api/config/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        mock_config_service.clear_cache.assert_called_once()
    
    def test_clear_error(self, test_client: TestClient, mock_config_service: MagicMock):
        """Test clearing cache with error."""
        mock_config_service.clear_cache.side_effect = ConfigurationError("Cache error")
        
        response = test_client.post("/api/config/cache/clear")
        assert response.status_code == 500
        assert response.json()["detail"] == "Cache error"


def test_service_not_initialized(test_client: TestClient):
    """Test endpoints when service is not initialized."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: None
    
    client = TestClient(app)
    endpoints = [
        "/api/config/types",
        "/api/config/test",
        "/api/config/test/validate",
        "/api/config/cache/clear"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"].lower()
