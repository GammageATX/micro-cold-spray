"""Tests for equipment service."""

import pytest
from unittest.mock import AsyncMock

from micro_cold_spray.api.base.exceptions import HardwareError, ValidationError
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.clients import PLCClient


@pytest.fixture
def mock_plc_client():
    """Create mock PLC client."""
    client = AsyncMock(spec=PLCClient)
    return client


@pytest.fixture
def equipment_service(mock_plc_client):
    """Create equipment service instance."""
    return EquipmentService(mock_plc_client)


class TestEquipmentService:
    """Test equipment service functionality."""

    @pytest.mark.asyncio
    async def test_set_gas_flow_main_valid(self, equipment_service, mock_plc_client):
        """Test setting main gas flow with valid value."""
        await equipment_service.set_gas_flow("main", 50.0)
        mock_plc_client.write_tag.assert_called_once_with("AOS32-0.1.2.1", 50.0)

    @pytest.mark.asyncio
    async def test_set_gas_flow_feeder_valid(self, equipment_service, mock_plc_client):
        """Test setting feeder gas flow with valid value."""
        await equipment_service.set_gas_flow("feeder", 5.0)
        mock_plc_client.write_tag.assert_called_once_with("AOS32-0.1.2.2", 5.0)

    @pytest.mark.asyncio
    async def test_set_gas_flow_invalid_type(self, equipment_service):
        """Test setting gas flow with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            await equipment_service.set_gas_flow("invalid", 50.0)
        assert "Invalid flow type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_gas_flow_main_invalid_value(self, equipment_service):
        """Test setting main gas flow with invalid value."""
        with pytest.raises(ValidationError) as exc_info:
            await equipment_service.set_gas_flow("main", 150.0)
        assert "main flow must be between" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_gas_flow_feeder_invalid_value(self, equipment_service):
        """Test setting feeder gas flow with invalid value."""
        with pytest.raises(ValidationError) as exc_info:
            await equipment_service.set_gas_flow("feeder", 15.0)
        assert "feeder flow must be between" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_gas_flow_hardware_error(self, equipment_service, mock_plc_client):
        """Test setting gas flow with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await equipment_service.set_gas_flow("main", 50.0)
        assert "Failed to set main gas flow" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_gas_valve_main_open(self, equipment_service, mock_plc_client):
        """Test opening main gas valve."""
        await equipment_service.set_gas_valve("main", True)
        mock_plc_client.write_tag.assert_called_once_with("MainSwitch", True)

    @pytest.mark.asyncio
    async def test_set_gas_valve_feeder_close(self, equipment_service, mock_plc_client):
        """Test closing feeder gas valve."""
        await equipment_service.set_gas_valve("feeder", False)
        mock_plc_client.write_tag.assert_called_once_with("FeederSwitch", False)

    @pytest.mark.asyncio
    async def test_set_gas_valve_invalid(self, equipment_service):
        """Test setting invalid gas valve."""
        with pytest.raises(ValidationError) as exc_info:
            await equipment_service.set_gas_valve("invalid", True)
        assert "Invalid valve" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_gas_valve_hardware_error(self, equipment_service, mock_plc_client):
        """Test gas valve control with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await equipment_service.set_gas_valve("main", True)
        assert "Failed to control main gas valve" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_control_vacuum_pump_mechanical_start(self, equipment_service, mock_plc_client):
        """Test starting mechanical pump."""
        await equipment_service.control_vacuum_pump("mechanical", True)
        mock_plc_client.write_tag.assert_called_once_with("MechPumpStart", True)

    @pytest.mark.asyncio
    async def test_control_vacuum_pump_booster_stop(self, equipment_service, mock_plc_client):
        """Test stopping booster pump."""
        await equipment_service.control_vacuum_pump("booster", False)
        mock_plc_client.write_tag.assert_called_once_with("BoosterPumpStop", True)

    @pytest.mark.asyncio
    async def test_control_vacuum_pump_invalid(self, equipment_service):
        """Test controlling invalid vacuum pump."""
        with pytest.raises(ValidationError) as exc_info:
            await equipment_service.control_vacuum_pump("invalid", True)
        assert "Invalid pump" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_control_vacuum_pump_hardware_error(self, equipment_service, mock_plc_client):
        """Test vacuum pump control with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await equipment_service.control_vacuum_pump("mechanical", True)
        assert "Failed to control mechanical pump" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_control_shutter_open(self, equipment_service, mock_plc_client):
        """Test opening shutter."""
        await equipment_service.control_shutter(True)
        mock_plc_client.write_tag.assert_called_once_with("Shutter", True)

    @pytest.mark.asyncio
    async def test_control_shutter_close(self, equipment_service, mock_plc_client):
        """Test closing shutter."""
        await equipment_service.control_shutter(False)
        mock_plc_client.write_tag.assert_called_once_with("Shutter", False)

    @pytest.mark.asyncio
    async def test_control_shutter_hardware_error(self, equipment_service, mock_plc_client):
        """Test shutter control with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await equipment_service.control_shutter(True)
        assert "Failed to control nozzle shutter" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_control_gate_valve_open(self, equipment_service, mock_plc_client):
        """Test opening gate valve."""
        await equipment_service.control_gate_valve("open")
        assert mock_plc_client.write_tag.call_count == 2
        mock_plc_client.write_tag.assert_any_call("Open", True)
        mock_plc_client.write_tag.assert_any_call("Partial", False)

    @pytest.mark.asyncio
    async def test_control_gate_valve_partial(self, equipment_service, mock_plc_client):
        """Test setting gate valve to partial."""
        await equipment_service.control_gate_valve("partial")
        assert mock_plc_client.write_tag.call_count == 2
        mock_plc_client.write_tag.assert_any_call("Open", False)
        mock_plc_client.write_tag.assert_any_call("Partial", True)

    @pytest.mark.asyncio
    async def test_control_gate_valve_closed(self, equipment_service, mock_plc_client):
        """Test closing gate valve."""
        await equipment_service.control_gate_valve("closed")
        assert mock_plc_client.write_tag.call_count == 2
        mock_plc_client.write_tag.assert_any_call("Open", False)
        mock_plc_client.write_tag.assert_any_call("Partial", False)

    @pytest.mark.asyncio
    async def test_control_gate_valve_invalid(self, equipment_service):
        """Test controlling gate valve with invalid position."""
        with pytest.raises(ValidationError) as exc_info:
            await equipment_service.control_gate_valve("invalid")
        assert "Invalid gate valve position" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_control_gate_valve_hardware_error(self, equipment_service, mock_plc_client):
        """Test gate valve control with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await equipment_service.control_gate_valve("open")
        assert "Failed to control gate valve" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_status_success(self, equipment_service, mock_plc_client):
        """Test successful status retrieval."""
        # Configure mock responses
        mock_plc_client.read_tag.side_effect = [
            50.0,   # MainFlowRate
            50.0,   # AOS32-0.1.2.1
            True,   # MainSwitch
            5.0,    # FeederFlowRate
            5.0,    # AOS32-0.1.2.2
            True,   # FeederSwitch
            100.0,  # MainGasPressure
            50.0,   # FeederPressure
            75.0,   # NozzlePressure
            80.0,   # RegulatorPressure
            0.1,    # ChamberPressure
            True,   # Open
            False,  # Partial
            True    # Shutter
        ]

        status = await equipment_service.get_status()

        # Verify structure and values
        assert "gas" in status
        assert "pressure" in status
        assert "vacuum" in status

        assert status["gas"]["main"]["flow"] == 50.0
        assert status["gas"]["main"]["setpoint"] == 50.0
        assert status["gas"]["main"]["valve"] is True

        assert status["gas"]["feeder"]["flow"] == 5.0
        assert status["gas"]["feeder"]["setpoint"] == 5.0
        assert status["gas"]["feeder"]["valve"] is True

        assert status["pressure"]["main"] == 100.0
        assert status["pressure"]["feeder"] == 50.0
        assert status["pressure"]["nozzle"] == 75.0
        assert status["pressure"]["regulator"] == 80.0
        assert status["pressure"]["chamber"] == 0.1

        assert status["vacuum"]["gate_valve"]["open"] is True
        assert status["vacuum"]["gate_valve"]["partial"] is False
        assert status["vacuum"]["shutter"] is True

    @pytest.mark.asyncio
    async def test_get_status_hardware_error(self, equipment_service, mock_plc_client):
        """Test status retrieval with hardware error."""
        mock_plc_client.read_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await equipment_service.get_status()
        assert "Failed to get equipment status" in str(exc_info.value)
