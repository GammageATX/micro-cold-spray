"""Tests for feeder service."""

import pytest
from unittest.mock import AsyncMock

from micro_cold_spray.api.base.exceptions import HardwareError, ValidationError
from micro_cold_spray.api.communication.services.feeder import FeederService
from micro_cold_spray.api.communication.clients import SSHClient


@pytest.fixture
def mock_ssh_client():
    """Create mock SSH client."""
    client = AsyncMock(spec=SSHClient)
    client.execute_command = AsyncMock()
    return client


@pytest.fixture
def feeder_service_set1(mock_ssh_client):
    """Create feeder service instance for hardware set 1."""
    return FeederService(mock_ssh_client, hardware_set=1)


@pytest.fixture
def feeder_service_set2(mock_ssh_client):
    """Create feeder service instance for hardware set 2."""
    return FeederService(mock_ssh_client, hardware_set=2)


class TestFeederService:
    """Test feeder service functionality."""

    def test_initialization_set1(self, feeder_service_set1):
        """Test initialization with hardware set 1."""
        assert feeder_service_set1._hardware_set == 1
        assert feeder_service_set1._freq_var == "P6"
        assert feeder_service_set1._start_var == "P10"
        assert feeder_service_set1._time_var == "P12"

    def test_initialization_set2(self, feeder_service_set2):
        """Test initialization with hardware set 2."""
        assert feeder_service_set2._hardware_set == 2
        assert feeder_service_set2._freq_var == "P106"
        assert feeder_service_set2._start_var == "P110"
        assert feeder_service_set2._time_var == "P112"

    @pytest.mark.asyncio
    async def test_start_feeder_valid(self, feeder_service_set1, mock_ssh_client):
        """Test starting feeder with valid frequency."""
        await feeder_service_set1.start_feeder(500.0)

        # Verify commands sent
        assert mock_ssh_client.execute_command.call_count == 3
        mock_ssh_client.execute_command.assert_any_call("P6=500.0")
        mock_ssh_client.execute_command.assert_any_call("P12=999")
        mock_ssh_client.execute_command.assert_any_call("P10=1")

    @pytest.mark.asyncio
    async def test_start_feeder_invalid_low(self, feeder_service_set1):
        """Test starting feeder with frequency too low."""
        with pytest.raises(ValidationError) as exc_info:
            await feeder_service_set1.start_feeder(100.0)
        assert "Frequency must be between 200 and 1200 Hz" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_feeder_invalid_high(self, feeder_service_set1):
        """Test starting feeder with frequency too high."""
        with pytest.raises(ValidationError) as exc_info:
            await feeder_service_set1.start_feeder(1500.0)
        assert "Frequency must be between 200 and 1200 Hz" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_feeder_hardware_error(self, feeder_service_set1, mock_ssh_client):
        """Test starting feeder with hardware error."""
        mock_ssh_client.execute_command.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await feeder_service_set1.start_feeder(500.0)
        assert "Failed to start feeder" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_feeder_success(self, feeder_service_set1, mock_ssh_client):
        """Test stopping feeder successfully."""
        await feeder_service_set1.stop_feeder()
        mock_ssh_client.execute_command.assert_called_once_with("P10=4")

    @pytest.mark.asyncio
    async def test_stop_feeder_hardware_error(self, feeder_service_set1, mock_ssh_client):
        """Test stopping feeder with hardware error."""
        mock_ssh_client.execute_command.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await feeder_service_set1.stop_feeder()
        assert "Failed to stop feeder" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_status_success(self, feeder_service_set1, mock_ssh_client):
        """Test getting feeder status successfully."""
        mock_ssh_client.execute_command.return_value = "500.0"
        status = await feeder_service_set1.get_status()
        assert status == {"frequency": 500.0}
        mock_ssh_client.execute_command.assert_called_once_with("echo $P6")

    @pytest.mark.asyncio
    async def test_get_status_hardware_error(self, feeder_service_set1, mock_ssh_client):
        """Test getting feeder status with hardware error."""
        mock_ssh_client.execute_command.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await feeder_service_set1.get_status()
        assert "Failed to get feeder status" in str(exc_info.value)
