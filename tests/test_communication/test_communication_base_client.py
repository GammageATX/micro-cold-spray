"""Tests for base communication client."""

import pytest
from typing import Dict, Any
from micro_cold_spray.api.base.service import BaseService
from micro_cold_spray.api.communication.clients.base import CommunicationClient
from micro_cold_spray.api.base.exceptions import ServiceError


class TestClient(CommunicationClient):
    """Concrete implementation for testing."""
    
    def __init__(self, config: Dict[str, Any], should_fail: bool = False):
        """Initialize test client.
        
        Args:
            config: Client configuration
            should_fail: If True, operations will raise errors
        """
        super().__init__("test", config)
        self.should_fail = should_fail
        self.connect_called = False
        self.disconnect_called = False
        self.read_calls = []
        self.write_calls = []
        self._tag_values = {}

    async def connect(self) -> None:
        """Test connect implementation."""
        if self.should_fail:
            raise ServiceError("Connect failed", {"device": "test"})
        self.connect_called = True
        self._connected = True

    async def disconnect(self) -> None:
        """Test disconnect implementation."""
        if self.should_fail:
            raise ServiceError("Disconnect failed", {"device": "test"})
        self.disconnect_called = True
        self._connected = False

    async def read_tag(self, tag: str) -> Any:
        """Test read implementation."""
        if self.should_fail:
            raise ServiceError("Read failed", {"device": "test", "tag": tag})
        self.read_calls.append(tag)
        return self._tag_values.get(tag, 0)

    async def write_tag(self, tag: str, value: Any) -> None:
        """Test write implementation."""
        if self.should_fail:
            raise ServiceError("Write failed", {"device": "test", "tag": tag})
        self.write_calls.append((tag, value))
        self._tag_values[tag] = value


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient({"test_tag": "test1"})


@pytest.fixture
def failing_client():
    """Create a test client that fails operations."""
    return TestClient({}, should_fail=True)


class TestCommunicationClient:
    """Test base communication client functionality."""

    def test_initialization(self, client):
        """Test client initialization."""
        assert isinstance(client, BaseService)
        assert client._service_name == "test_client"
        assert not client.is_connected
        assert client._config == {"test_tag": "test1"}

    def test_initialization_empty_config(self):
        """Test initialization with empty config."""
        client = TestClient(None)
        assert client._config == {}

    @pytest.mark.asyncio
    async def test_start_stop(self, client):
        """Test service lifecycle."""
        # Test start
        await client._start()
        assert client.connect_called
        assert client.is_connected

        # Test stop
        await client._stop()
        assert client.disconnect_called
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_start_failure(self, failing_client):
        """Test service start failure."""
        with pytest.raises(ServiceError) as exc_info:
            await failing_client._start()
        assert "Failed to start" in str(exc_info.value)
        assert not failing_client.is_connected

    @pytest.mark.asyncio
    async def test_stop_failure(self, failing_client):
        """Test service stop failure."""
        failing_client._connected = True  # Force connected state
        with pytest.raises(ServiceError) as exc_info:
            await failing_client._stop()
        assert "Failed to stop" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tag_operations(self, client):
        """Test tag read/write operations."""
        # Test write
        await client.write_tag("test1", 42)
        assert ("test1", 42) in client.write_calls
        
        # Test read
        value = await client.read_tag("test1")
        assert "test1" in client.read_calls
        assert value == 42

    @pytest.mark.asyncio
    async def test_tag_operation_failures(self, failing_client):
        """Test tag operation failures."""
        # Test write failure
        with pytest.raises(ServiceError) as exc_info:
            await failing_client.write_tag("test1", 42)
        assert "Write failed" in str(exc_info.value)

        # Test read failure
        with pytest.raises(ServiceError) as exc_info:
            await failing_client.read_tag("test1")
        assert "Read failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_check(self, client):
        """Test connection health check."""
        # Test when disconnected
        assert not await client.check_connection()

        # Test when connected
        client._connected = True
        assert await client.check_connection()

        # Test with test tag
        value = await client.read_tag("test1")
        assert "test1" in client.read_calls
        assert value == 0  # Default value

    @pytest.mark.asyncio
    async def test_connection_check_failure(self, failing_client):
        """Test connection check with failures."""
        # When disconnected
        assert not await failing_client.check_connection()

        # When connected but operations fail
        failing_client._connected = True
        failing_client._config["test_tag"] = "test1"  # Add test tag to trigger read
        assert not await failing_client.check_connection()
