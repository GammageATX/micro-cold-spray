"""Tests for PLC communication client."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from micro_cold_spray.api.base.exceptions import ValidationError, ServiceError
from micro_cold_spray.api.communication.clients.plc import PLCClient


@pytest.fixture
def tag_file(tmp_path):
    """Create a temporary tag file for testing."""
    tag_file = tmp_path / "tags.csv"
    tag_file.write_text("Tag,Address,Type\nTest,TEST,REAL")
    return tag_file


@pytest.fixture
def valid_config(tag_file):
    """Create valid PLC configuration."""
    return {
        "ip": "192.168.1.100",
        "tag_file": str(tag_file),
        "polling_interval": 1.0,
        "retry": {
            "delay": 0.1,
            "max_attempts": 2
        },
        "timeout": 1.0
    }


@pytest.fixture
def mock_plc():
    """Create mock ProductivityPLC instance."""
    with patch('micro_cold_spray.api.communication.clients.plc.ProductivityPLC') as mock:
        plc = AsyncMock()
        mock.return_value = plc
        yield plc


class TestPLCClient:
    """Test PLC client functionality."""

    def test_initialization_success(self, valid_config, mock_plc):
        """Test successful client initialization."""
        client = PLCClient(valid_config)
        assert client._ip == "192.168.1.100"
        assert isinstance(client._tag_file, Path)
        assert client._polling_interval == 1.0
        assert client._retry_delay == 0.1
        assert client._max_attempts == 2
        assert client._timeout == 1.0
        assert not client.is_connected

    def test_initialization_missing_fields(self):
        """Test initialization with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            PLCClient({})
        assert "Missing required PLC config field" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            PLCClient({"ip": "192.168.1.100"})
        assert "Missing required PLC config field" in str(exc_info.value)

    def test_initialization_invalid_tag_file(self, valid_config):
        """Test initialization with nonexistent tag file."""
        config = valid_config.copy()
        config["tag_file"] = "nonexistent.csv"
        with pytest.raises(ValidationError) as exc_info:
            PLCClient(config)
        assert "Tag file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_success(self, valid_config, mock_plc):
        """Test successful connection."""
        mock_plc.get.return_value = {"Test": 42}
        client = PLCClient(valid_config)
        await client.connect()
        assert client.is_connected
        mock_plc.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, valid_config, mock_plc):
        """Test connection failure."""
        mock_plc.get.side_effect = Exception("Connection failed")
        client = PLCClient(valid_config)
        with pytest.raises(ServiceError) as exc_info:
            await client.connect()
        assert "Failed to connect to PLC" in str(exc_info.value)
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, valid_config, mock_plc):
        """Test disconnection."""
        client = PLCClient(valid_config)
        client._connected = True
        await client.disconnect()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_read_tag_success(self, valid_config, mock_plc):
        """Test successful tag read."""
        mock_plc.get.return_value = {"Test": 42}
        client = PLCClient(valid_config)
        client._connected = True
        value = await client.read_tag("Test")
        assert value == 42
        mock_plc.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_tag_not_found(self, valid_config, mock_plc):
        """Test reading nonexistent tag."""
        mock_plc.get.return_value = {"Test": 42}
        client = PLCClient(valid_config)
        client._connected = True
        with pytest.raises(ValidationError) as exc_info:
            await client.read_tag("NonexistentTag")
        assert "Tag NonexistentTag not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_tag_failure(self, valid_config, mock_plc):
        """Test tag read failure."""
        mock_plc.get.side_effect = Exception("Read failed")
        client = PLCClient(valid_config)
        client._connected = True
        with pytest.raises(ServiceError) as exc_info:
            await client.read_tag("Test")
        assert "Failed to read tag Test" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_tag_cancelled(self, valid_config, mock_plc):
        """Test cancelled tag read."""
        mock_plc.get.side_effect = asyncio.CancelledError()
        client = PLCClient(valid_config)
        client._connected = True
        value = await client.read_tag("Test")
        assert value is None

    @pytest.mark.asyncio
    async def test_write_tag_success(self, valid_config, mock_plc):
        """Test successful tag write."""
        client = PLCClient(valid_config)
        client._connected = True
        await client.write_tag("Test", 42)
        mock_plc.set.assert_called_once_with({"Test": 42})

    @pytest.mark.asyncio
    async def test_write_tag_failure(self, valid_config, mock_plc):
        """Test tag write failure."""
        mock_plc.set.side_effect = Exception("Write failed")
        client = PLCClient(valid_config)
        client._connected = True
        with pytest.raises(ServiceError) as exc_info:
            await client.write_tag("Test", 42)
        assert "Failed to write tag Test" in str(exc_info.value)
        mock_plc.set.assert_called_once_with({"Test": 42})
