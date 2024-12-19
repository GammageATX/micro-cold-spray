"""Tests for configuration router."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime
import yaml
import copy
import asyncio
import json

from micro_cold_spray.api.config.endpoints.config_endpoints import router, get_config_service, init_router
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.models import ConfigData, ConfigUpdate, ConfigValidationResult
from micro_cold_spray.api.base.base_errors import ConfigError


@pytest.fixture
def mock_config_service():
    """Create a mock config service."""
    service = MagicMock(spec=ConfigService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "config"
    service.version = "1.0.0"
    
    # Define uptime property getter
    def get_uptime(self):
        if not self.is_running or self.start_time is None:
            return None
        return (datetime.now() - self.start_time).total_seconds()
    
    # Set uptime as a property
    type(service).uptime = property(get_uptime)
    
    # Mock health check to return proper status
    async def mock_health_check():
        response = {
            "status": "stopped" if not service.is_running else "ok",
            "uptime": service.uptime,
            "memory_usage": 0,
            "service_info": {
                "name": service._service_name,
                "version": service.version,
                "running": service.is_running,
                "error": None
            }
        }
        
        if service.is_running:
            response.update({
                "services": {
                    "cache": True,
                    "file": True,
                    "schema": True,
                    "registry": True,
                    "format": True
                },
                "schema_loaded": True,
                "last_error": None,
                "last_update": None
            })
        
        return response
    
    service.check_health = mock_health_check
    
    return service


@pytest.fixture
def test_client(mock_config_service):
    """Create a test client with mock service."""
    from fastapi import FastAPI
    app = FastAPI()
    
    # Initialize router
    init_router(app)
    
    # Mock get_config_service to return our mock
    def mock_get_service():
        return mock_config_service
    
    with patch('micro_cold_spray.api.config.endpoints.config_endpoints.get_config_service', mock_get_service):
        # Include router in app
        app.include_router(router)
        
        return TestClient(app)


def test_get_config_types(test_client):
    """Test getting available config types."""
    response = test_client.get("/config/types")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6  # application, hardware, file_format, process, state, tags
    
    # Verify each config type has required fields
    for config_type in data:
        assert "id" in config_type
        assert "name" in config_type


def test_health_check_success(test_client, mock_config_service):
    """Test successful health check."""
    # Mock check_config_access to return True
    mock_config_service.check_config_access = AsyncMock(return_value=True)
    mock_config_service.is_running = True
    
    response = test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime" in data
    assert "memory_usage" in data
    assert data["service_info"]["name"] == "config"
    assert data["service_info"]["version"] == "1.0.0"
    assert data["service_info"]["running"] is True


@pytest.mark.asyncio
async def test_update_config_with_backup(test_client, tmp_path):
    """Test updating configuration with backup creation."""
    # Create a real config service with temp directory
    from micro_cold_spray.api.config.services.config_file_service import ConfigFileService
    
    # Set up test directories
    test_config_dir = tmp_path / "test_config"
    test_config_dir.mkdir()
    test_schema_dir = test_config_dir / "schemas"
    test_schema_dir.mkdir()
    test_backup_dir = test_config_dir / "backups"
    test_backup_dir.mkdir()
    
    # Create test schema for all required types
    test_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "application": {
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "enum": ["test", "development", "production"]},
                            "version": {"type": "string"}
                        }
                    },
                    "info": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
    
    # Write schema for all required types
    for schema_type in ["application", "hardware", "process", "tags", "state", "file_format"]:
        schema_dest = test_schema_dir / f"{schema_type}.json"
        with open(schema_dest, "w") as f:
            json.dump(test_schema, f)
    
    # Create test config file
    test_config = {
        "application": {
            "environment": {
                "mode": "development",
                "version": "1.0.0"
            },
            "info": {
                "version": "1.0.0"
            }
        }
    }
    test_config_dest = test_config_dir / "application.yaml"
    with open(test_config_dest, "w") as f:
        yaml.dump(test_config, f)
    
    # Create and initialize service with test paths
    service = ConfigService(service_name="config")
    service._config_dir = test_config_dir
    service._schema_dir = test_schema_dir
    service._file_service._config_dir = test_config_dir
    service._file_service._backup_dir = test_backup_dir
    service._schema_service._schema_dir = test_schema_dir
    
    # Mock get_config_service to return our real service
    def mock_get_service():
        return service
    
    with patch('micro_cold_spray.api.config.endpoints.config_endpoints.get_config_service', mock_get_service):
        # Test updating config with backup
        update = ConfigUpdate(
            config_type="application",
            data={
                "environment": {
                    "mode": "production",
                    "version": "1.0.1"
                },
                "info": {
                    "version": "1.0.1"
                }
            },
            backup=True
        )
        
        response = test_client.post("/config/application", json=update.model_dump())
        assert response.status_code == 200
        
        # Verify backup was created
        backup_files = list(test_backup_dir.glob("*.bak"))
        assert len(backup_files) == 1
        
        # Verify config was updated
        with open(test_config_dest, "r") as f:
            updated_config = yaml.safe_load(f)
        assert updated_config["application"]["environment"]["mode"] == "production"
        assert updated_config["application"]["environment"]["version"] == "1.0.1"
