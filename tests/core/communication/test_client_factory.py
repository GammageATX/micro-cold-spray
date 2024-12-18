"""Tests for communication client factory."""

import pytest
from pathlib import Path
from unittest.mock import patch
from micro_cold_spray.api.base.exceptions import ValidationError
from micro_cold_spray.api.communication.clients.factory import (
    create_plc_client,
    create_ssh_client,
    create_client
)
from micro_cold_spray.api.communication.clients import (
    PLCClient,
    SSHClient,
    MockPLCClient,
    MockSSHClient
)


@pytest.fixture
def tag_file(tmp_path):
    """Create a temporary tag file for testing."""
    tag_file = tmp_path / "tags.csv"
    tag_file.write_text("Tag,Address,Type\nTest,TEST,REAL")
    return tag_file


class TestClientFactory:
    """Test client factory functionality."""

    @patch('micro_cold_spray.api.communication.clients.plc.ProductivityPLC')
    def test_create_plc_client(self, mock_plc, tag_file):
        """Test PLC client creation."""
        # Test with valid config
        config = {
            "ip": "192.168.1.100",
            "tag_file": str(tag_file),
            "polling_interval": 1.0
        }
        client = create_plc_client(config)
        assert isinstance(client, PLCClient)
        assert client._ip == "192.168.1.100"
        assert Path(client._tag_file).name == "tags.csv"
        assert client._polling_interval == 1.0

        # Test mock client
        mock_client = create_plc_client({}, use_mock=True)
        assert isinstance(mock_client, MockPLCClient)

        # Test missing config
        with pytest.raises(ValidationError) as exc_info:
            create_plc_client({})
        assert "Missing hardware configuration" in str(exc_info.value)

        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            create_plc_client({"ip": "192.168.1.100"})
        assert "Missing required PLC config fields" in str(exc_info.value)

        # Test nonexistent tag file
        bad_config = {
            "ip": "192.168.1.100",
            "tag_file": "nonexistent.csv",
            "polling_interval": 1.0
        }
        with pytest.raises(ValidationError) as exc_info:
            create_plc_client(bad_config)
        assert "Tag file not found" in str(exc_info.value)

    def test_create_ssh_client(self):
        """Test SSH client creation."""
        # Test with valid config
        config = {
            "host": "192.168.1.200",
            "username": "admin",
            "password": "secret"
        }
        client = create_ssh_client(config)
        assert isinstance(client, SSHClient)
        assert client._host == "192.168.1.200"
        assert client._username == "admin"
        assert client._password == "secret"

        # Test mock client
        mock_client = create_ssh_client({}, use_mock=True)
        assert isinstance(mock_client, MockSSHClient)

        # Test missing config
        with pytest.raises(ValidationError) as exc_info:
            create_ssh_client({})
        assert "Missing hardware configuration" in str(exc_info.value)

        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            create_ssh_client({"host": "192.168.1.200"})
        assert "Missing required SSH config fields" in str(exc_info.value)

    @patch('micro_cold_spray.api.communication.clients.plc.ProductivityPLC')
    def test_create_client(self, mock_plc, tag_file):
        """Test generic client creation."""
        # Test PLC client
        plc_config = {
            "ip": "192.168.1.100",
            "tag_file": str(tag_file),
            "polling_interval": 1.0
        }
        plc_client = create_client("plc", plc_config)
        assert isinstance(plc_client, PLCClient)

        # Test SSH client
        ssh_config = {
            "host": "192.168.1.200",
            "username": "admin",
            "password": "secret"
        }
        ssh_client = create_client("ssh", ssh_config)
        assert isinstance(ssh_client, SSHClient)

        # Test mock clients
        mock_plc = create_client("plc", {}, use_mock=True)
        assert isinstance(mock_plc, MockPLCClient)

        mock_ssh = create_client("ssh", {}, use_mock=True)
        assert isinstance(mock_ssh, MockSSHClient)

        # Test invalid client type
        with pytest.raises(ValidationError) as exc_info:
            create_client("invalid", {})
        assert "Invalid client type" in str(exc_info.value)
