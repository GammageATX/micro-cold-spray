"""Tests for SSH communication client."""

import pytest
from unittest.mock import patch, AsyncMock
from micro_cold_spray.api.base.exceptions import ValidationError, ServiceError
from micro_cold_spray.api.communication.clients.ssh import SSHClient


class MockSSHResult:
    """Mock SSH command result."""
    def __init__(self, stdout="", stderr="", exit_status=0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_status = exit_status


@pytest.fixture
def key_file(tmp_path):
    """Create a temporary SSH key file."""
    key_file = tmp_path / "id_rsa"
    key_file.write_text("TEST SSH KEY")
    return key_file


@pytest.fixture
def valid_password_config():
    """Create valid SSH config with password."""
    return {
        "host": "192.168.1.200",
        "port": 22,
        "username": "admin",
        "password": "secret"
    }


@pytest.fixture
def valid_key_config(key_file):
    """Create valid SSH config with key file."""
    return {
        "host": "192.168.1.200",
        "port": 22,
        "username": "admin",
        "key_file": str(key_file)
    }


@pytest.fixture
def mock_ssh():
    """Create mock SSH connection."""
    with patch('micro_cold_spray.api.communication.clients.ssh.asyncssh') as mock:
        connection = AsyncMock()
        mock.connect = AsyncMock(return_value=connection)
        yield mock, connection


class TestSSHClient:
    """Test SSH client functionality."""

    def test_initialization_with_password(self, valid_password_config):
        """Test initialization with password authentication."""
        client = SSHClient(valid_password_config)
        assert client._host == "192.168.1.200"
        assert client._port == 22
        assert client._username == "admin"
        assert client._password == "secret"
        assert client._key_file is None  # No key file for password auth
        assert not client.is_connected

    def test_initialization_with_key(self, valid_key_config, key_file):
        """Test initialization with key file authentication."""
        client = SSHClient(valid_key_config)
        assert client._host == "192.168.1.200"
        assert client._port == 22
        assert client._username == "admin"
        assert client._key_file == key_file
        assert not client._password
        assert not client.is_connected

    def test_initialization_missing_fields(self):
        """Test initialization with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            SSHClient({})
        assert "Missing required SSH config field" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SSHClient({"host": "192.168.1.200"})
        assert "Missing required SSH config field" in str(exc_info.value)

    def test_initialization_no_auth(self):
        """Test initialization with no authentication method."""
        config = {
            "host": "192.168.1.200",
            "username": "admin",
            "key_file": "nonexistent.key"  # Invalid key file
        }
        with pytest.raises(ValidationError) as exc_info:
            SSHClient(config)
        assert "No valid authentication method" in str(exc_info.value)

    def test_initialization_invalid_key_file(self, valid_key_config):
        """Test initialization with nonexistent key file."""
        config = valid_key_config.copy()
        config["key_file"] = "nonexistent.key"
        with pytest.raises(ValidationError) as exc_info:
            SSHClient(config)
        assert "No valid authentication method" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_with_password(self, valid_password_config, mock_ssh):
        """Test connection with password authentication."""
        mock_asyncssh, mock_conn = mock_ssh
        client = SSHClient(valid_password_config)

        await client.connect()
        assert client.is_connected
        mock_asyncssh.connect.assert_called_once_with(
            "192.168.1.200",
            username="admin",
            port=22,
            password="secret",
            known_hosts=None
        )

    @pytest.mark.asyncio
    async def test_connect_with_key(self, valid_key_config, mock_ssh, key_file):
        """Test connection with key file authentication."""
        mock_asyncssh, mock_conn = mock_ssh
        client = SSHClient(valid_key_config)

        await client.connect()
        assert client.is_connected
        mock_asyncssh.connect.assert_called_once_with(
            "192.168.1.200",
            username="admin",
            port=22,
            client_keys=[str(key_file)],
            known_hosts=None
        )

    @pytest.mark.asyncio
    async def test_connect_failure(self, valid_password_config, mock_ssh):
        """Test connection failure."""
        mock_asyncssh, _ = mock_ssh
        mock_asyncssh.connect.side_effect = Exception("Connection failed")
        client = SSHClient(valid_password_config)

        with pytest.raises(ServiceError) as exc_info:
            await client.connect()
        assert "Failed to connect" in str(exc_info.value)
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, valid_password_config, mock_ssh):
        """Test successful disconnection."""
        mock_asyncssh, mock_conn = mock_ssh
        client = SSHClient(valid_password_config)
        await client.connect()

        await client.disconnect()
        assert not client.is_connected
        mock_conn.close.assert_called_once()  # Synchronous call
        mock_conn.wait_closed.assert_awaited_once()  # Async call

    @pytest.mark.asyncio
    async def test_disconnect_failure(self, valid_password_config, mock_ssh):
        """Test disconnection failure."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.wait_closed.side_effect = Exception("Disconnect failed")
        client = SSHClient(valid_password_config)
        await client.connect()

        with pytest.raises(ServiceError) as exc_info:
            await client.disconnect()
        assert "Error disconnecting" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_tag_not_connected(self, valid_password_config):
        """Test reading tag when not connected."""
        client = SSHClient(valid_password_config)
        with pytest.raises(ServiceError) as exc_info:
            await client.read_tag("test")
        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_tag_success(self, valid_password_config, mock_ssh):
        """Test successful tag read."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.run.return_value = MockSSHResult(stdout="42.0\n")
        client = SSHClient(valid_password_config)
        await client.connect()

        value = await client.read_tag("test")
        assert value == 42.0
        mock_conn.run.assert_called_once_with("read_tag test")

    @pytest.mark.asyncio
    async def test_read_tag_command_failure(self, valid_password_config, mock_ssh):
        """Test tag read with command failure."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.run.return_value = MockSSHResult(
            stderr="Tag not found",
            exit_status=1
        )
        client = SSHClient(valid_password_config)
        await client.connect()

        with pytest.raises(ValidationError) as exc_info:
            await client.read_tag("test")
        assert "Failed to read tag" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_read_tag_parse_failure(self, valid_password_config, mock_ssh):
        """Test tag read with value parsing failure."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.run.return_value = MockSSHResult(stdout="invalid")
        client = SSHClient(valid_password_config)
        await client.connect()

        with pytest.raises(ServiceError) as exc_info:
            await client.read_tag("test")
        assert "Failed to read tag" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_tag_not_connected(self, valid_password_config):
        """Test writing tag when not connected."""
        client = SSHClient(valid_password_config)
        with pytest.raises(ServiceError) as exc_info:
            await client.write_tag("test", 42)
        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_tag_success(self, valid_password_config, mock_ssh):
        """Test successful tag write."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.run.return_value = MockSSHResult()
        client = SSHClient(valid_password_config)
        await client.connect()

        await client.write_tag("test", 42)
        mock_conn.run.assert_called_once_with("write_tag test 42")

    @pytest.mark.asyncio
    async def test_write_tag_command_failure(self, valid_password_config, mock_ssh):
        """Test tag write with command failure."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.run.return_value = MockSSHResult(
            stderr="Tag not found",
            exit_status=1
        )
        client = SSHClient(valid_password_config)
        await client.connect()

        with pytest.raises(ValidationError) as exc_info:
            await client.write_tag("test", 42)
        assert "Failed to write tag" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_tag_unexpected_error(self, valid_password_config, mock_ssh):
        """Test write tag with unexpected error."""
        mock_asyncssh, mock_conn = mock_ssh
        mock_conn.run.side_effect = RuntimeError("Unexpected error")
        client = SSHClient(valid_password_config)
        await client.connect()

        with pytest.raises(ServiceError) as exc_info:
            await client.write_tag("test", 42)
        assert "Failed to write tag test" in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)
