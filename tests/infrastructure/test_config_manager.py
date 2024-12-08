"""Test configuration manager functionality."""
import pytest

from micro_cold_spray.core.exceptions import ConfigurationError


@pytest.mark.asyncio
class TestConfigManager:
    """Test ConfigManager functionality."""

    @pytest.mark.asyncio
    async def test_load_config(self, config_manager):
        """Test loading real configs from config directory."""
        # Test loading hardware config
        hardware_config = await config_manager.get_config("hardware")
        assert hardware_config is not None
        assert "hardware" in hardware_config
        assert "network" in hardware_config["hardware"]
        assert "plc" in hardware_config["hardware"]["network"]
        assert "ip" in hardware_config["hardware"]["network"]["plc"]

        # Test loading invalid config
        with pytest.raises(ConfigurationError):
            await config_manager.get_config("invalid")

    @pytest.mark.asyncio
    async def test_config_validation(self, config_manager):
        """Test config validation."""
        # Test valid config
        hardware_config = await config_manager.get_config("hardware")
        assert hardware_config is not None
        assert "hardware" in hardware_config
        assert "network" in hardware_config["hardware"]
        assert "plc" in hardware_config["hardware"]["network"]
        assert "ip" in hardware_config["hardware"]["network"]["plc"]

        # Test invalid config
        with pytest.raises(ConfigurationError):
            await config_manager.get_config("invalid")
