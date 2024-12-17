"""Tests for data collection service."""

from datetime import datetime
import pytest
from unittest.mock import Mock, AsyncMock

from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError, StorageError
from micro_cold_spray.api.config import ConfigService


# Test data
SAMPLE_EVENT = SprayEvent(
    sequence_id="test_sequence_1",
    spray_index=1,
    timestamp=datetime.now(),
    x_pos=1.0,
    y_pos=2.0,
    z_pos=3.0,
    pressure=100.0,
    temperature=25.0,
    flow_rate=5.0,
    status="completed"
)

COLLECTION_PARAMS = {
    "mode": "continuous",
    "interval": 1.0,
    "duration": 60.0
}


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    storage = Mock()
    storage.initialize = AsyncMock()
    storage.save_spray_event = AsyncMock()
    storage.get_spray_events = AsyncMock(return_value=[])
    storage.check_connection = AsyncMock(return_value=True)
    storage.check_storage = AsyncMock(return_value=True)
    storage.check_health = AsyncMock(return_value={"status": "ok"})
    return storage


@pytest.fixture
def mock_config():
    """Create a mock config service."""
    config = Mock(spec=ConfigService)
    config.get_service_config = AsyncMock(return_value={"test": "config"})
    return config


@pytest.fixture
async def service(mock_storage, mock_config):
    """Create and start a test service."""
    service = DataCollectionService(mock_storage, mock_config)
    await service.start()
    yield service
    await service.stop()


class TestServiceStateValidation:
    """Test service state validation and transitions."""
    
    @pytest.fixture
    async def service(self, mock_storage, mock_config):
        """Create and start a test service."""
        service = DataCollectionService(mock_storage, mock_config)
        await service.start()
        yield service
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_service_state_transitions(self, mock_storage, mock_config):
        """Test service state transitions through lifecycle."""
        service = DataCollectionService(mock_storage, mock_config)
        
        # Initial state
        assert not service.is_running
        assert service.active_session is None
        
        # After start
        await service.start()
        assert service.is_running
        assert service.active_session is None
        
        # Start collection
        session = await service.start_collection("test_sequence", COLLECTION_PARAMS)
        assert service.is_running
        assert service.active_session is not None
        assert service.active_session.sequence_id == "test_sequence"
        assert session.sequence_id == "test_sequence"
        
        # Stop collection
        await service.stop_collection()
        assert service.is_running
        assert service.active_session is None
        
        # Stop service
        await service.stop()
        assert not service.is_running
        assert service.active_session is None
    
    @pytest.mark.asyncio
    async def test_state_validation_during_operations(self, service):
        """Test state validation during various operations."""
        # Test operations before collection starts
        with pytest.raises(DataCollectionError) as exc_info:
            await service.record_spray_event(SAMPLE_EVENT)
        assert "No active collection session" in str(exc_info.value)
        
        # Start collection and test operations
        await service.start_collection("test_sequence", COLLECTION_PARAMS)
        
        # Test starting another collection while one is active
        with pytest.raises(DataCollectionError) as exc_info:
            await service.start_collection("another_sequence", COLLECTION_PARAMS)
        assert "Collection already in progress" in str(exc_info.value)
        
        # Stop collection and test operations
        await service.stop_collection()
        with pytest.raises(DataCollectionError) as exc_info:
            await service.record_spray_event(SAMPLE_EVENT)
        assert "No active collection session" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_state_recovery_after_errors(self, service, mock_storage):
        """Test service state recovery after errors."""
        # Simulate storage error during collection
        mock_storage.save_spray_event.side_effect = StorageError("Test error")
        
        await service.start_collection("test_sequence", COLLECTION_PARAMS)
        
        # Attempt operation that will fail
        with pytest.raises(DataCollectionError):
            await service.record_spray_event(SAMPLE_EVENT)
        
        # Service should still be running but no active session
        assert service.is_running
        assert service.active_session is not None  # Session remains until explicitly stopped
        
        # Should be able to stop collection
        await service.stop_collection()
        assert service.active_session is None
        
        # Should be able to start new collection
        mock_storage.save_spray_event.side_effect = None  # Clear error
        await service.start_collection("new_sequence", COLLECTION_PARAMS)
        assert service.active_session is not None
        assert service.active_session.sequence_id == "new_sequence"


class TestServiceHealthChecks:
    """Test service health monitoring and checks."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service, mock_storage):
        """Test health check when service is healthy."""
        mock_storage.check_connection.return_value = True
        mock_storage.check_storage.return_value = True
        mock_storage.check_health.return_value = {
            "status": "ok",
            "connections": 5,
            "active_queries": 0
        }
        
        health = await service.check_health()
        assert health["status"] == "ok"
        assert health.get("error") is None
        
        # With active collection
        session = await service.start_collection("test_sequence", COLLECTION_PARAMS)
        assert session is not None
        
        # Update mock to include active sequence
        mock_storage.check_health.return_value = {
            "status": "ok",
            "connections": 5,
            "active_queries": 1,
            "active_sequence": "test_sequence"
        }
        
        health = await service.check_health()
        assert health["status"] == "ok"
        assert health.get("error") is None
        assert health.get("active_sequence") == "test_sequence"
    
    @pytest.mark.asyncio
    async def test_health_check_storage_error(self, service, mock_storage):
        """Test health check when storage is unhealthy."""
        error_msg = "Connection failed"
        mock_storage.check_connection.side_effect = StorageError(error_msg)
        mock_storage.check_storage.return_value = False
        mock_storage.check_health.side_effect = StorageError(error_msg)
        
        health = await service.check_health()
        assert health["status"] == "error"
        assert error_msg in str(health.get("error", ""))
    
    @pytest.mark.asyncio
    async def test_health_check_not_running(self, mock_storage, mock_config):
        """Test health check when service is not running."""
        service = DataCollectionService(mock_storage, mock_config)
        health = await service.check_health()
        assert health["status"] == "stopped"
        assert health.get("error") is None
    
    @pytest.mark.asyncio
    async def test_storage_check(self, service, mock_storage):
        """Test storage connection check."""
        # Test successful check
        mock_storage.check_connection.return_value = True
        mock_storage.check_storage.return_value = True
        mock_storage.check_health.return_value = {
            "status": "ok",
            "connections": 5,
            "active_queries": 0
        }
        
        assert await service.check_storage()
        
        # Test failed check
        error_msg = "Test error"
        mock_storage.check_connection.side_effect = StorageError(error_msg)
        mock_storage.check_storage.return_value = False
        mock_storage.check_health.return_value = {
            "status": "error",
            "error": error_msg
        }
        
        assert not await service.check_storage()
        
        # Test recovery
        mock_storage.check_connection.side_effect = None
        mock_storage.check_connection.return_value = True
        mock_storage.check_storage.return_value = True
        mock_storage.check_health.return_value = {
            "status": "ok",
            "connections": 5,
            "active_queries": 0
        }
        
        assert await service.check_storage()
