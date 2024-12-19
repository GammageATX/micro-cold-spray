"""Unit tests for Config Service functionality."""

import pytest
from tests.base import BaseServiceTest
from micro_cold_spray.core.errors.exceptions import ConfigurationError


@pytest.mark.unit
@pytest.mark.service
class TestConfigService(BaseServiceTest):
    """Test Config Service functionality."""

    @pytest.fixture
    def config_service(self, mock_base_service):
        """Create test config service."""
        return mock_base_service

    def test_config_service_initialization(self, config_service):
        """Test config service initialization."""
        assert config_service.service_name == "test_service"
        assert config_service.version == "1.0.0"
        assert not config_service.is_running

    @pytest.mark.asyncio
    async def test_config_service_startup(self, config_service):
        """Test config service startup."""
        await config_service.start()
        self.assert_service_running()

        # Verify configuration is loaded
        assert hasattr(config_service, "config")
        assert config_service.config is not None

    @pytest.mark.asyncio
    async def test_config_service_shutdown(self, config_service):
        """Test config service shutdown."""
        await config_service.start()
        await config_service.stop()
        self.assert_service_stopped()

    @pytest.mark.asyncio
    async def test_config_service_reload(self, config_service):
        """Test config service reload."""
        await config_service.start()
        
        # Mock configuration change
        config_service.config.set("test_key", "test_value")
        
        # Reload configuration
        await config_service.reload_config()
        
        # Verify configuration is reloaded
        assert config_service.config.get("test_key") == "test_value"

    @pytest.mark.asyncio
    async def test_config_service_validation(self, config_service):
        """Test config service validation."""
        await config_service.start()
        
        # Test required settings validation
        required_settings = [
            "application.name",
            "application.version",
            "services.config.host",
            "services.config.port"
        ]
        
        for setting in required_settings:
            assert config_service.validate_setting(setting)

    @pytest.mark.asyncio
    async def test_config_service_error_handling(self, config_service):
        """Test config service error handling."""
        # Test invalid configuration
        with pytest.raises(ConfigurationError):
            config_service.config.set("services.config.port", "invalid_port")
            await config_service.validate_config()

    @pytest.mark.asyncio
    async def test_config_service_health_check(self, config_service):
        """Test config service health check."""
        await config_service.start()
        health = await config_service.check_health()
        
        assert health["status"] == "ok"
        assert health["service_info"]["name"] == "test_service"
        assert health["service_info"]["version"] == "1.0.0"
        assert health["service_info"]["running"] is True

    @pytest.mark.asyncio
    async def test_config_service_environment(self, config_service):
        """Test config service environment handling."""
        await config_service.start()
        
        # Test environment-specific configuration
        assert config_service.get_environment() == "test"
        
        # Test environment switching
        config_service.set_environment("production")
        assert config_service.get_environment() == "production"

    @pytest.mark.asyncio
    async def test_config_service_updates(self, config_service):
        """Test config service update handling."""
        await config_service.start()
        
        # Test configuration update
        updates = {
            "application": {
                "name": "updated_app",
                "version": "2.0.0"
            }
        }
        
        await config_service.update_config(updates)
        assert config_service.config.application.name == "updated_app"
        assert config_service.config.application.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_config_service_secrets(self, config_service):
        """Test config service secrets handling."""
        await config_service.start()
        
        # Test secrets management
        secret_key = "test_api_key"
        secret_value = "secret123"
        
        await config_service.set_secret(secret_key, secret_value)
        assert await config_service.get_secret(secret_key) == secret_value
        
        # Test secret masking in logs/output
        config_str = str(config_service.config)
        assert secret_value not in config_str
