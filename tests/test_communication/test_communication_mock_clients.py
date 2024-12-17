"""Tests for mock communication clients."""

import pytest
from micro_cold_spray.api.communication.clients.mock import MockPLCClient, MockSSHClient


@pytest.fixture
def mock_plc():
    """Create a mock PLC client."""
    return MockPLCClient({})


@pytest.fixture
def mock_ssh():
    """Create a mock SSH client."""
    return MockSSHClient({})


class TestMockPLCClient:
    """Test mock PLC client functionality."""

    async def test_connection(self, mock_plc):
        """Test connection and disconnection."""
        assert not mock_plc._connected
        await mock_plc.connect()
        assert mock_plc._connected
        await mock_plc.disconnect()
        assert not mock_plc._connected

    async def test_default_values(self, mock_plc):
        """Test default tag values are initialized correctly."""
        # Test boolean system status tags
        assert await mock_plc.read_tag("MainSwitch") is False
        assert await mock_plc.read_tag("FeederSwitch") is False
        assert await mock_plc.read_tag("VentSwitch") is False
        assert await mock_plc.read_tag("NozzleSelect") is False

        # Test motion control tags
        assert await mock_plc.read_tag("XAxis.InProgress") is False
        assert await mock_plc.read_tag("YAxis.Complete") is False
        assert await mock_plc.read_tag("AMC.Ax1Position") == 0

        # Test pressure and flow tags (12-bit values)
        assert await mock_plc.read_tag("MainGasPressure") == 4095  # 100 psi
        assert await mock_plc.read_tag("RegulatorPressure") == 3276  # 80 psi
        assert await mock_plc.read_tag("FeederPressure") == 819  # 0.2 torr

    async def test_boolean_tag_write(self, mock_plc):
        """Test writing to boolean tags."""
        await mock_plc.write_tag("MainSwitch", True)
        assert await mock_plc.read_tag("MainSwitch") is True

        await mock_plc.write_tag("FeederSwitch", 1)  # Should convert to True
        assert await mock_plc.read_tag("FeederSwitch") is True

        await mock_plc.write_tag("VentSwitch", False)
        assert await mock_plc.read_tag("VentSwitch") is False

    async def test_analog_tag_write(self, mock_plc):
        """Test writing to analog tags with 12-bit validation."""
        # Test valid values
        await mock_plc.write_tag("MainGasPressure", 2000)
        assert await mock_plc.read_tag("MainGasPressure") == 2000

        # Test value clamping
        await mock_plc.write_tag("RegulatorPressure", 5000)  # Above max
        assert await mock_plc.read_tag("RegulatorPressure") == 4095

        await mock_plc.write_tag("FeederPressure", -100)  # Below min
        assert await mock_plc.read_tag("FeederPressure") == 0

    async def test_unknown_tag(self, mock_plc):
        """Test reading/writing unknown tags."""
        assert await mock_plc.read_tag("NonexistentTag") == 0
        await mock_plc.write_tag("NonexistentTag", 100)  # Should log warning but not error

    async def test_error_simulation(self, mock_plc):
        """Test error simulation functionality."""
        await mock_plc.connect()
        assert mock_plc._connected

        with pytest.raises(ConnectionError, match="Simulated connection loss"):
            await mock_plc.simulate_error("connection_loss")
        assert not mock_plc._connected


class TestMockSSHClient:
    """Test mock SSH client functionality."""

    async def test_connection(self, mock_ssh):
        """Test connection and disconnection."""
        assert not mock_ssh._connected
        await mock_ssh.connect()
        assert mock_ssh._connected
        await mock_ssh.disconnect()
        assert not mock_ssh._connected

    async def test_default_values(self, mock_ssh):
        """Test default P tag values are initialized correctly."""
        # Test Feeder 1 P tags
        assert await mock_ssh.read_tag("P6") == 200  # Initial frequency
        assert await mock_ssh.read_tag("P10") == 4  # Initially stopped
        assert await mock_ssh.read_tag("P12") == 999  # Default run time

        # Test Feeder 2 P tags
        assert await mock_ssh.read_tag("P106") == 200
        assert await mock_ssh.read_tag("P110") == 4
        assert await mock_ssh.read_tag("P112") == 999

    async def test_frequency_tag_write(self, mock_ssh):
        """Test writing to frequency P tags with validation."""
        # Test valid values
        await mock_ssh.write_tag("P6", 500)
        assert await mock_ssh.read_tag("P6") == 500

        await mock_ssh.write_tag("P106", 1000)
        assert await mock_ssh.read_tag("P106") == 1000

        # Test value clamping
        await mock_ssh.write_tag("P6", 100)  # Below min
        assert await mock_ssh.read_tag("P6") == 200

        await mock_ssh.write_tag("P106", 1500)  # Above max
        assert await mock_ssh.read_tag("P106") == 1200

    async def test_start_stop_tag_write(self, mock_ssh):
        """Test writing to start/stop P tags with validation."""
        # Test valid values
        await mock_ssh.write_tag("P10", 1)  # Start
        assert await mock_ssh.read_tag("P10") == 1

        await mock_ssh.write_tag("P110", 4)  # Stop
        assert await mock_ssh.read_tag("P110") == 4

        # Test invalid values (should convert to valid ones)
        await mock_ssh.write_tag("P10", 2)  # Invalid - should become 1
        assert await mock_ssh.read_tag("P10") == 1

        await mock_ssh.write_tag("P110", 0)  # Invalid - should become 1
        assert await mock_ssh.read_tag("P110") == 1

    async def test_time_tag_write(self, mock_ssh):
        """Test writing to time P tags with validation."""
        # Test valid values
        await mock_ssh.write_tag("P12", 500)
        assert await mock_ssh.read_tag("P12") == 500

        await mock_ssh.write_tag("P112", 100)
        assert await mock_ssh.read_tag("P112") == 100

        # Test negative values (should become 0)
        await mock_ssh.write_tag("P12", -100)
        assert await mock_ssh.read_tag("P12") == 0

    async def test_unknown_tag(self, mock_ssh):
        """Test reading/writing unknown tags."""
        assert await mock_ssh.read_tag("NonexistentTag") == 0
        await mock_ssh.write_tag("NonexistentTag", 100)  # Should log warning but not error
