"""Tests for tag mapping service."""

import pytest
from unittest.mock import AsyncMock
from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    service.get_config = AsyncMock()
    return service


@pytest.fixture
def sample_tag_config():
    """Create sample tag configuration."""
    return {
        "tag_groups": {
            "gas_control": {
                "main_flow": {
                    "type": "float",
                    "access": "read",
                    "description": "Main gas flow measured",
                    "unit": "SLPM",
                    "range": [0.0, 100.0],
                    "mapped": True,
                    "plc_tag": "GAS_FLOW_PV"
                },
                "setpoint": {
                    "type": "float",
                    "access": "read/write",
                    "description": "Main gas flow setpoint",
                    "unit": "SLPM",
                    "range": [0.0, 100.0],
                    "mapped": True,
                    "plc_tag": "GAS_FLOW_SP"
                }
            },
            "feeder": {
                "powder": {
                    "type": "float",
                    "access": "read/write",
                    "description": "Powder feeder control",
                    "unit": "RPM",
                    "range": [0.0, 50.0],
                    "mapped": True,
                    "ssh": {
                        "freq_var": "FREQ_VAR",
                        "start_var": "START_VAR",
                        "time_var": "TIME_VAR"
                    }
                }
            },
            "status": {
                "state": {
                    "type": "string",
                    "access": "read",
                    "description": "System state",
                    "options": ["IDLE", "RUNNING", "ERROR"],
                    "mapped": False
                }
            }
        }
    }


@pytest.fixture
async def tag_mapping_service(mock_config_service, sample_tag_config):
    """Create tag mapping service instance."""
    mock_config_service.get_config.return_value = sample_tag_config
    service = TagMappingService(mock_config_service)
    await service.start()
    return service


class TestTagMappingService:
    """Test tag mapping service functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, tag_mapping_service):
        """Test service initialization."""
        # Verify PLC mappings
        assert tag_mapping_service._hw_to_mapped["GAS_FLOW_PV"] == "gas_control.main_flow"
        assert tag_mapping_service._hw_to_mapped["GAS_FLOW_SP"] == "gas_control.setpoint"
        assert tag_mapping_service._mapped_to_hw["gas_control.main_flow"] == "GAS_FLOW_PV"
        assert tag_mapping_service._mapped_to_hw["gas_control.setpoint"] == "GAS_FLOW_SP"

        # Verify PLC tags set
        assert "gas_control.main_flow" in tag_mapping_service._plc_tags
        assert "gas_control.setpoint" in tag_mapping_service._plc_tags

        # Verify SSH/feeder mappings - all variables map to same tag
        assert tag_mapping_service._hw_to_mapped["FREQ_VAR"] == "feeder.powder"
        assert tag_mapping_service._hw_to_mapped["START_VAR"] == "feeder.powder"
        assert tag_mapping_service._hw_to_mapped["TIME_VAR"] == "feeder.powder"
        # Last variable in the list becomes the hardware tag
        assert tag_mapping_service._mapped_to_hw["feeder.powder"] == "TIME_VAR"

        # Verify feeder tags set
        assert "feeder.powder" in tag_mapping_service._feeder_tags

    @pytest.mark.asyncio
    async def test_initialization_error(self, mock_config_service):
        """Test initialization with error."""
        mock_config_service.get_config.side_effect = ServiceError("Failed to get config")
        service = TagMappingService(mock_config_service)
        
        with pytest.raises(ServiceError) as exc_info:
            await service.start()
        assert "Failed to get config" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialization_invalid_config(self, mock_config_service):
        """Test initialization with invalid config."""
        mock_config_service.get_config.return_value = {"invalid": "config"}
        service = TagMappingService(mock_config_service)
        await service.start()  # Should not raise error, just build empty mappings
        assert len(service._mapped_to_hw) == 0

    @pytest.mark.asyncio
    async def test_service_cleanup(self, tag_mapping_service):
        """Test service cleanup on stop."""
        await tag_mapping_service.stop()
        assert len(tag_mapping_service._hw_to_mapped) == 0
        assert len(tag_mapping_service._mapped_to_hw) == 0
        assert len(tag_mapping_service._plc_tags) == 0
        assert len(tag_mapping_service._feeder_tags) == 0

    def test_to_mapped_name_plc(self, tag_mapping_service):
        """Test converting hardware tag to mapped name for PLC tags."""
        mapped_name = tag_mapping_service.to_mapped_name("GAS_FLOW_PV")
        assert mapped_name == "gas_control.main_flow"

    def test_to_mapped_name_ssh(self, tag_mapping_service):
        """Test converting hardware tag to mapped name for SSH tags."""
        # All SSH variables map to the same tag
        mapped_name = tag_mapping_service.to_mapped_name("FREQ_VAR")
        assert mapped_name == "feeder.powder"
        mapped_name = tag_mapping_service.to_mapped_name("START_VAR")
        assert mapped_name == "feeder.powder"
        mapped_name = tag_mapping_service.to_mapped_name("TIME_VAR")
        assert mapped_name == "feeder.powder"

    def test_to_mapped_name_invalid(self, tag_mapping_service):
        """Test converting invalid hardware tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_mapping_service.to_mapped_name("INVALID_TAG")
        assert "No mapping for hardware tag" in str(exc_info.value)

    def test_to_hardware_tag_plc(self, tag_mapping_service):
        """Test converting mapped name to hardware tag for PLC tags."""
        hw_tag = tag_mapping_service.to_hardware_tag("gas_control.main_flow")
        assert hw_tag == "GAS_FLOW_PV"

    def test_to_hardware_tag_ssh(self, tag_mapping_service):
        """Test converting mapped name to hardware tag for SSH tags."""
        # For SSH tags, the last variable in the list becomes the hardware tag
        hw_tag = tag_mapping_service.to_hardware_tag("feeder.powder")
        assert hw_tag == "TIME_VAR"  # Last variable in the list

    def test_to_hardware_tag_invalid(self, tag_mapping_service):
        """Test converting invalid mapped name."""
        with pytest.raises(ValidationError) as exc_info:
            tag_mapping_service.to_hardware_tag("invalid.tag")
        assert "No mapping for tag" in str(exc_info.value)

    def test_is_plc_tag_valid(self, tag_mapping_service):
        """Test checking valid PLC tag."""
        assert tag_mapping_service.is_plc_tag("gas_control.main_flow")
        assert not tag_mapping_service.is_plc_tag("feeder.powder")

    def test_is_plc_tag_invalid(self, tag_mapping_service):
        """Test checking invalid PLC tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_mapping_service.is_plc_tag("invalid.tag")
        assert "Unknown tag" in str(exc_info.value)

    def test_is_feeder_tag_valid(self, tag_mapping_service):
        """Test checking valid feeder tag."""
        assert tag_mapping_service.is_feeder_tag("feeder.powder")
        assert not tag_mapping_service.is_feeder_tag("gas_control.main_flow")

    def test_is_feeder_tag_invalid(self, tag_mapping_service):
        """Test checking invalid feeder tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_mapping_service.is_feeder_tag("invalid.tag")
        assert "Unknown tag" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_mappings_empty_config(self, tag_mapping_service):
        """Test building mappings with empty config."""
        await tag_mapping_service._build_mappings({})
        assert len(tag_mapping_service._hw_to_mapped) == 0
        assert len(tag_mapping_service._mapped_to_hw) == 0
        assert len(tag_mapping_service._plc_tags) == 0
        assert len(tag_mapping_service._feeder_tags) == 0

    @pytest.mark.asyncio
    async def test_build_mappings_unmapped_tags(self, tag_mapping_service, sample_tag_config):
        """Test building mappings with unmapped tags."""
        # Modify config to include unmapped tag
        sample_tag_config["tag_groups"]["test"] = {
            "unmapped": {
                "type": "float",
                "access": "read",
                "mapped": False
            }
        }
        await tag_mapping_service._build_mappings(sample_tag_config)
        assert "test.unmapped" not in tag_mapping_service._mapped_to_hw

    @pytest.mark.asyncio
    async def test_build_mappings_invalid_tag_def(self, tag_mapping_service, sample_tag_config):
        """Test building mappings with invalid tag definition."""
        # Add invalid tag definition
        sample_tag_config["tag_groups"]["invalid"] = {
            "tag": "not_a_dict"  # Invalid - should be dict
        }
        # Should raise ServiceError
        with pytest.raises(ServiceError) as exc_info:
            await tag_mapping_service._build_mappings(sample_tag_config)
        assert "Failed to build tag mappings" in str(exc_info.value)
