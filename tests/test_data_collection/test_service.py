"""Tests for data collection service."""

import asyncio
from datetime import datetime
import pytest
from unittest.mock import Mock, AsyncMock

from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent, CollectionSession
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
    return storage


@pytest.fixture
def mock_config():
    """Create a mock config service."""
    config = Mock(spec=ConfigService)
    config.get_service_config = AsyncMock(return_value={"test": "config"})
    return config


@pytest.fixture
async def service(mock_storage, mock_config):
    """Create a service instance for testing."""
    service = DataCollectionService(mock_storage, mock_config)
    await service.start()
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_service_lifecycle(mock_storage):
    """Test service start/stop lifecycle."""
    service = DataCollectionService(mock_storage)
    
    # Test start
    await service.start()
    assert service.is_running
    mock_storage.initialize.assert_called_once()
    
    # Test stop
    await service.stop()
    assert not service.is_running
    assert service.active_session is None


@pytest.mark.asyncio
async def test_service_with_config(mock_storage, mock_config):
    """Test service with config service."""
    service = DataCollectionService(mock_storage, mock_config)
    mock_config.get_service_config.assert_not_called()
    
    await service.configure({"test": "config"})
    assert service.config == {"test": "config"}


@pytest.mark.asyncio
async def test_service_stop_error(mock_storage):
    """Test error handling during service stop."""
    service = DataCollectionService(mock_storage)
    await service.start()
    await service.start_collection("test", {})
    
    # Simulate error during stop
    def stop_error(*args, **kwargs):
        raise Exception("Stop error")
    
    service.stop_collection = stop_error  # type: ignore
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.stop()
    assert "Failed to stop service" in str(exc_info.value)


@pytest.mark.asyncio
async def test_start_collection_error(service):
    """Test error handling during collection start."""
    # Simulate error during start
    service._active_session = Mock()  # Force active session to trigger error
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.start_collection("test", {})
    assert "Collection already in progress" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stop_collection_error(service):
    """Test error handling during collection stop."""
    # Simulate error during stop
    service._active_session = None  # Force no active session to trigger error
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.stop_collection()
    assert "No active collection" in str(exc_info.value)


@pytest.mark.asyncio
async def test_record_event_storage_error(service, mock_storage):
    """Test storage error handling during event recording."""
    await service.start_collection(SAMPLE_EVENT.sequence_id, COLLECTION_PARAMS)
    mock_storage.save_spray_event.side_effect = Exception("Generic error")
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.record_spray_event(SAMPLE_EVENT)
    assert "Failed to record spray event" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_events_storage_error(service, mock_storage):
    """Test storage error handling during event retrieval."""
    mock_storage.get_spray_events.side_effect = Exception("Storage error")
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.get_sequence_events("test")
    assert "Failed to get sequence events" in str(exc_info.value)


@pytest.mark.asyncio
async def test_check_storage_error(service, mock_storage):
    """Test error handling during storage check."""
    # Test storage initialization error
    mock_storage.initialize.side_effect = Exception("Init error")
    service = DataCollectionService(mock_storage)
    
    with pytest.raises(StorageError) as exc_info:
        await service.start()
    assert "Failed to initialize storage" in str(exc_info.value)


@pytest.mark.asyncio
async def test_start_collection(service):
    """Test starting data collection."""
    session = await service.start_collection("test_sequence", COLLECTION_PARAMS)
    
    assert isinstance(session, CollectionSession)
    assert session.sequence_id == "test_sequence"
    assert session.collection_params == COLLECTION_PARAMS
    assert service.active_session == session


@pytest.mark.asyncio
async def test_start_collection_already_active(service):
    """Test starting collection when one is already active."""
    await service.start_collection("test_sequence_1", COLLECTION_PARAMS)
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.start_collection("test_sequence_2", COLLECTION_PARAMS)
    assert "Collection already in progress" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stop_collection(service):
    """Test stopping data collection."""
    await service.start_collection("test_sequence", COLLECTION_PARAMS)
    assert service.active_session is not None
    
    await service.stop_collection()
    assert service.active_session is None


@pytest.mark.asyncio
async def test_stop_collection_no_active(service):
    """Test stopping collection when none is active."""
    with pytest.raises(DataCollectionError) as exc_info:
        await service.stop_collection()
    assert "No active collection" in str(exc_info.value)


@pytest.mark.asyncio
async def test_record_spray_event(service, mock_storage):
    """Test recording a spray event."""
    await service.start_collection(SAMPLE_EVENT.sequence_id, COLLECTION_PARAMS)
    await service.record_spray_event(SAMPLE_EVENT)
    
    mock_storage.save_spray_event.assert_called_once_with(SAMPLE_EVENT)


@pytest.mark.asyncio
async def test_record_event_no_active_session(service):
    """Test recording event without active session."""
    with pytest.raises(DataCollectionError) as exc_info:
        await service.record_spray_event(SAMPLE_EVENT)
    assert "No active collection session" in str(exc_info.value)


@pytest.mark.asyncio
async def test_record_event_wrong_sequence(service):
    """Test recording event for wrong sequence."""
    await service.start_collection("different_sequence", COLLECTION_PARAMS)
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.record_spray_event(SAMPLE_EVENT)
    assert "Event sequence ID does not match" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_sequence_events(service, mock_storage):
    """Test retrieving sequence events."""
    mock_storage.get_spray_events.return_value = [SAMPLE_EVENT]
    
    events = await service.get_sequence_events(SAMPLE_EVENT.sequence_id)
    assert len(events) == 1
    assert events[0] == SAMPLE_EVENT
    mock_storage.get_spray_events.assert_called_once_with(SAMPLE_EVENT.sequence_id)


@pytest.mark.asyncio
async def test_storage_error_handling(service, mock_storage):
    """Test handling of storage errors."""
    mock_storage.save_spray_event.side_effect = StorageError("Storage failed")
    await service.start_collection(SAMPLE_EVENT.sequence_id, COLLECTION_PARAMS)
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.record_spray_event(SAMPLE_EVENT)
    assert "Failed to record spray event" in str(exc_info.value)


@pytest.mark.asyncio
async def test_check_storage(service, mock_storage):
    """Test storage health check."""
    # Test successful check
    assert await service.check_storage()
    mock_storage.save_spray_event.assert_called_once()
    
    # Test failed check
    mock_storage.save_spray_event.side_effect = Exception("Storage error")
    assert not await service.check_storage()


@pytest.mark.asyncio
async def test_service_not_running():
    """Test operations when service is not running."""
    service = DataCollectionService(Mock())
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.start_collection("test", {})
    assert "Service not running" in str(exc_info.value)
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.record_spray_event(SAMPLE_EVENT)
    assert "Service not running" in str(exc_info.value)
    
    with pytest.raises(DataCollectionError) as exc_info:
        await service.get_sequence_events("test")
    assert "Service not running" in str(exc_info.value)
    
    assert not await service.check_storage()


@pytest.mark.asyncio
async def test_concurrent_operations(service, mock_storage):
    """Test concurrent service operations."""
    await service.start_collection(SAMPLE_EVENT.sequence_id, COLLECTION_PARAMS)
    
    # Test concurrent event recording
    events = [SAMPLE_EVENT.model_copy(update={"spray_index": i}) for i in range(5)]
    await asyncio.gather(*[service.record_spray_event(event) for event in events])
    
    assert mock_storage.save_spray_event.call_count == 5
