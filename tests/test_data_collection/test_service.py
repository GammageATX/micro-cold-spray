"""Tests for data collection service."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.storage import DataStorage
from micro_cold_spray.api.data_collection.models import SprayEvent, CollectionSession
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError
from . import TEST_SEQUENCE_ID, TEST_TIMESTAMP, TEST_COLLECTION_PARAMS


class TestDataCollectionService:
    """Test data collection service."""
    
    @pytest.fixture
    def mock_storage(self) -> AsyncMock:
        """Create mock storage."""
        mock = AsyncMock(spec=DataStorage)
        mock.initialize = AsyncMock()
        mock.save_spray_event = AsyncMock()
        mock.update_spray_event = AsyncMock()
        mock.get_spray_events = AsyncMock(return_value=[])
        return mock
        
    @pytest.fixture
    def service(self, mock_storage: AsyncMock) -> DataCollectionService:
        """Create service instance with mock storage."""
        return DataCollectionService(mock_storage)
    
    @pytest.mark.asyncio
    async def test_start_collection(self, service: DataCollectionService) -> None:
        """Test starting collection session."""
        # Start service
        await service._start()
        
        # Test successful start
        session = await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        assert isinstance(session, CollectionSession)
        assert session.sequence_id == TEST_SEQUENCE_ID
        assert session.collection_params == TEST_COLLECTION_PARAMS
        
        # Test starting when already active
        with pytest.raises(DataCollectionError) as exc_info:
            await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        assert "Collection already in progress" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_stop_collection(self, service: DataCollectionService) -> None:
        """Test stopping collection."""
        # Start service and collection
        await service._start()
        await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        
        # Test successful stop
        await service.stop_collection()
        assert service.active_session is None
        
        # Test stopping when no active session
        with pytest.raises(DataCollectionError) as exc_info:
            await service.stop_collection()
        assert "No active collection" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_record_spray_event(self, service: DataCollectionService, mock_storage: AsyncMock) -> None:
        """Test recording spray events."""
        # Start service and collection
        await service._start()
        await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        
        # Create test event
        event = SprayEvent(
            sequence_id=TEST_SEQUENCE_ID,
            spray_index=1,
            timestamp=TEST_TIMESTAMP,
            x_pos=10.0,
            y_pos=20.0,
            z_pos=30.0,
            pressure=100.0,
            temperature=25.0,
            flow_rate=5.0,
            status="active"
        )
        
        # Test recording with active session
        await service.record_spray_event(event)
        mock_storage.save_spray_event.assert_called_once_with(event)
        
        # Test sequence ID mismatch
        wrong_event = SprayEvent(
            sequence_id="wrong_sequence",
            spray_index=2,
            timestamp=datetime.now(),
            x_pos=10.0,
            y_pos=20.0,
            z_pos=30.0,
            pressure=100.0,
            temperature=25.0,
            flow_rate=5.0,
            status="active"
        )
        with pytest.raises(DataCollectionError) as exc_info:
            await service.record_spray_event(wrong_event)
        assert "Event sequence ID does not match" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_get_sequence_events(self, service: DataCollectionService, mock_storage: AsyncMock) -> None:
        """Test retrieving sequence events."""
        # Start service
        await service._start()
        
        # Setup mock return value
        events = [
            SprayEvent(
                sequence_id=TEST_SEQUENCE_ID,
                spray_index=i,
                timestamp=TEST_TIMESTAMP,
                x_pos=float(i),
                y_pos=float(i),
                z_pos=float(i),
                pressure=100.0,
                temperature=25.0,
                flow_rate=5.0,
                status="active"
            )
            for i in range(3)
        ]
        mock_storage.get_spray_events.return_value = events
        
        # Test successful retrieval
        retrieved = await service.get_sequence_events(TEST_SEQUENCE_ID)
        assert len(retrieved) == 3
        mock_storage.get_spray_events.assert_called_once_with(TEST_SEQUENCE_ID)
        
        # Test with non-existent sequence
        mock_storage.get_spray_events.return_value = []
        empty = await service.get_sequence_events("non_existent")
        assert len(empty) == 0
