"""Tests for motion service."""

import pytest
from unittest.mock import AsyncMock

from micro_cold_spray.api.base.exceptions import HardwareError, ValidationError
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.clients import PLCClient


@pytest.fixture
def mock_plc_client():
    """Create mock PLC client."""
    client = AsyncMock(spec=PLCClient)
    return client


@pytest.fixture
def motion_service(mock_plc_client):
    """Create motion service instance."""
    return MotionService(mock_plc_client)


class TestMotionService:
    """Test motion service functionality."""

    @pytest.mark.asyncio
    async def test_move_axis_x_valid(self, motion_service, mock_plc_client):
        """Test valid X axis move."""
        await motion_service.move_axis("x", 100.0, 50.0)

        # Verify commands sent
        assert mock_plc_client.write_tag.call_count == 5
        mock_plc_client.write_tag.assert_any_call("XAxis.Velocity", 50.0)
        mock_plc_client.write_tag.assert_any_call("XAxis.Accel", 100)
        mock_plc_client.write_tag.assert_any_call("XAxis.Decel", 100)
        mock_plc_client.write_tag.assert_any_call("AMC.Ax1Position", 100.0)
        mock_plc_client.write_tag.assert_any_call("MoveX", True)

    @pytest.mark.asyncio
    async def test_move_axis_y_valid(self, motion_service, mock_plc_client):
        """Test valid Y axis move."""
        await motion_service.move_axis("y", 200.0, 75.0)

        # Verify commands sent
        assert mock_plc_client.write_tag.call_count == 5
        mock_plc_client.write_tag.assert_any_call("YAxis.Velocity", 75.0)
        mock_plc_client.write_tag.assert_any_call("YAxis.Accel", 100)
        mock_plc_client.write_tag.assert_any_call("YAxis.Decel", 100)
        mock_plc_client.write_tag.assert_any_call("AMC.Ax2Position", 200.0)
        mock_plc_client.write_tag.assert_any_call("MoveY", True)

    @pytest.mark.asyncio
    async def test_move_axis_z_valid(self, motion_service, mock_plc_client):
        """Test valid Z axis move."""
        await motion_service.move_axis("z", -50.0, 25.0)

        # Verify commands sent
        assert mock_plc_client.write_tag.call_count == 5
        mock_plc_client.write_tag.assert_any_call("ZAxis.Velocity", 25.0)
        mock_plc_client.write_tag.assert_any_call("ZAxis.Accel", 100)
        mock_plc_client.write_tag.assert_any_call("ZAxis.Decel", 100)
        mock_plc_client.write_tag.assert_any_call("AMC.Ax3Position", -50.0)
        mock_plc_client.write_tag.assert_any_call("MoveZ", True)

    @pytest.mark.asyncio
    async def test_move_axis_invalid_axis(self, motion_service):
        """Test move with invalid axis."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_axis("invalid", 100.0, 50.0)
        assert "Invalid axis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_axis_invalid_position_low(self, motion_service):
        """Test move with position too low."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_axis("x", -1500.0, 50.0)
        assert "Position must be between -1000 and 1000 mm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_axis_invalid_position_high(self, motion_service):
        """Test move with position too high."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_axis("x", 1500.0, 50.0)
        assert "Position must be between -1000 and 1000 mm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_axis_invalid_velocity_low(self, motion_service):
        """Test move with velocity too low."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_axis("x", 100.0, -10.0)
        assert "Velocity must be between 0 and 100 mm/s" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_axis_invalid_velocity_high(self, motion_service):
        """Test move with velocity too high."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_axis("x", 100.0, 150.0)
        assert "Velocity must be between 0 and 100 mm/s" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_axis_hardware_error(self, motion_service, mock_plc_client):
        """Test move with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await motion_service.move_axis("x", 100.0, 50.0)
        assert "Failed to move x axis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_valid(self, motion_service, mock_plc_client):
        """Test valid XY move."""
        await motion_service.move_xy(100.0, 200.0, 50.0)

        # Verify commands sent
        assert mock_plc_client.write_tag.call_count == 5
        mock_plc_client.write_tag.assert_any_call("XYMove.XPosition", 100.0)
        mock_plc_client.write_tag.assert_any_call("XYMove.YPosition", 200.0)
        mock_plc_client.write_tag.assert_any_call("XYMove.LINVelocity", 50.0)
        mock_plc_client.write_tag.assert_any_call("XYMove.LINRamps", 0.5)
        mock_plc_client.write_tag.assert_any_call("MoveXY", True)

    @pytest.mark.asyncio
    async def test_move_xy_invalid_x_low(self, motion_service):
        """Test XY move with X position too low."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_xy(-1500.0, 200.0, 50.0)
        assert "X position must be between -1000 and 1000 mm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_invalid_x_high(self, motion_service):
        """Test XY move with X position too high."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_xy(1500.0, 200.0, 50.0)
        assert "X position must be between -1000 and 1000 mm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_invalid_y_low(self, motion_service):
        """Test XY move with Y position too low."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_xy(100.0, -1500.0, 50.0)
        assert "Y position must be between -1000 and 1000 mm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_invalid_y_high(self, motion_service):
        """Test XY move with Y position too high."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_xy(100.0, 1500.0, 50.0)
        assert "Y position must be between -1000 and 1000 mm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_invalid_velocity_low(self, motion_service):
        """Test XY move with velocity too low."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_xy(100.0, 200.0, -10.0)
        assert "Velocity must be between 0 and 100 mm/s" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_invalid_velocity_high(self, motion_service):
        """Test XY move with velocity too high."""
        with pytest.raises(ValidationError) as exc_info:
            await motion_service.move_xy(100.0, 200.0, 150.0)
        assert "Velocity must be between 0 and 100 mm/s" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_move_xy_hardware_error(self, motion_service, mock_plc_client):
        """Test XY move with hardware error."""
        mock_plc_client.write_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await motion_service.move_xy(100.0, 200.0, 50.0)
        assert "Failed to execute XY move" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_status_success(self, motion_service, mock_plc_client):
        """Test successful status retrieval."""
        # Configure mock responses
        mock_plc_client.read_tag.side_effect = [
            100.0,  # x position
            200.0,  # y position
            -50.0,  # z position
            True,   # x moving
            False,  # y moving
            True,   # z moving
            False,  # x complete
            True,   # y complete
            False,  # z complete
            1,      # x status
            2,      # y status
            3       # z status
        ]

        status = await motion_service.get_status()

        # Verify structure and values
        assert "position" in status
        assert "moving" in status
        assert "complete" in status
        assert "status" in status

        assert status["position"]["x"] == 100.0
        assert status["position"]["y"] == 200.0
        assert status["position"]["z"] == -50.0

        assert status["moving"]["x"] is True
        assert status["moving"]["y"] is False
        assert status["moving"]["z"] is True

        assert status["complete"]["x"] is False
        assert status["complete"]["y"] is True
        assert status["complete"]["z"] is False

        assert status["status"]["x"] == 1
        assert status["status"]["y"] == 2
        assert status["status"]["z"] == 3

        # Verify read_tag calls
        assert mock_plc_client.read_tag.call_count == 12
        mock_plc_client.read_tag.assert_any_call("AMC.Ax1Position")
        mock_plc_client.read_tag.assert_any_call("AMC.Ax2Position")
        mock_plc_client.read_tag.assert_any_call("AMC.Ax3Position")
        mock_plc_client.read_tag.assert_any_call("XAxis.InProgress")
        mock_plc_client.read_tag.assert_any_call("YAxis.InProgress")
        mock_plc_client.read_tag.assert_any_call("ZAxis.InProgress")
        mock_plc_client.read_tag.assert_any_call("XAxis.Complete")
        mock_plc_client.read_tag.assert_any_call("YAxis.Complete")
        mock_plc_client.read_tag.assert_any_call("ZAxis.Complete")
        mock_plc_client.read_tag.assert_any_call("AMC.Ax1AxisStatus")
        mock_plc_client.read_tag.assert_any_call("AMC.Ax2AxisStatus")
        mock_plc_client.read_tag.assert_any_call("AMC.Ax3AxisStatus")

    @pytest.mark.asyncio
    async def test_get_status_hardware_error(self, motion_service, mock_plc_client):
        """Test status retrieval with hardware error."""
        mock_plc_client.read_tag.side_effect = Exception("Hardware error")
        with pytest.raises(HardwareError) as exc_info:
            await motion_service.get_status()
        assert "Failed to get motion status" in str(exc_info.value)
