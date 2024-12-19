"""Tests for configuration endpoints."""

import pytest
from typing import Dict, Any
from .test_base import BaseAPITest

class TestConfigEndpoints(BaseAPITest):
    """Test cases for configuration endpoints."""
    
    @pytest.fixture
    def sample_config(self) -> Dict[str, Any]:
        """Sample configuration data for testing."""
        return {
            "application": {
                "name": "micro-cold-spray",
                "version": "1.0.0",
                "settings": {
                    "log_level": "INFO",
                    "debug_mode": False
                }
            }
        }
    
    def test_get_config_types(self):
        """Test getting available configuration types."""
        response = self.client.get("/api/config/types")
        self.assert_success_response(response)
        data = response.json()
        
        assert "types" in data
        types = data["types"]
        assert isinstance(types, list)
        
        # Verify required config types exist
        type_ids = [t["id"] for t in types]
        required_types = ["application", "hardware", "operation"]
        for req_type in required_types:
            assert req_type in type_ids
    
    def test_get_config(self, sample_config):
        """Test getting configuration by type."""
        response = self.client.get("/api/config/application")
        self.assert_success_response(response)
        data = response.json()
        
        assert data == sample_config["application"]
    
    def test_update_config(self, sample_config):
        """Test updating configuration."""
        config_update = {
            "settings": {
                "log_level": "DEBUG",
                "debug_mode": True
            }
        }
        
        response = self.client.patch(
            "/api/config/application",
            json=config_update
        )
        self.assert_success_response(response)
        
        # Verify config was updated
        get_response = self.client.get("/api/config/application")
        updated_config = get_response.json()
        assert updated_config["settings"]["log_level"] == "DEBUG"
        assert updated_config["settings"]["debug_mode"] is True
    
    def test_invalid_config_type(self):
        """Test getting configuration with invalid type."""
        response = self.client.get("/api/config/invalid_type")
        self.assert_error_response(
            response,
            status_code=404,
            error_message="Configuration type 'invalid_type' not found"
        )
    
    def test_invalid_config_update(self):
        """Test updating configuration with invalid data."""
        invalid_update = {
            "invalid_field": "value"
        }
        
        response = self.client.patch(
            "/api/config/application",
            json=invalid_update
        )
        self.assert_error_response(response, status_code=422)
    
    @pytest.mark.asyncio
    async def test_async_config_operations(self, sample_config):
        """Test async configuration operations."""
        # Get config
        get_response = await self.async_client.get("/api/config/application")
        await self.assert_async_success_response(get_response)
        
        # Update config
        update = {
            "settings": {
                "log_level": "DEBUG"
            }
        }
        update_response = await self.async_client.patch(
            "/api/config/application",
            json=update
        )
        await self.assert_async_success_response(update_response)
    
    def test_config_backup(self):
        """Test configuration backup endpoint."""
        response = self.client.post("/api/config/backup")
        self.assert_success_response(response)
        data = response.json()
        
        assert "backup_path" in data
        assert isinstance(data["backup_path"], str)
        assert data["backup_path"].endswith(".json") 