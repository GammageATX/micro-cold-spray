"""Integration tests for data collection API."""

import pytest
from typing import AsyncGenerator, List

from micro_cold_spray.api.data_collection.storage import DatabaseStorage
from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError, StorageError
from . import TEST_SEQUENCE_ID, TEST_TIMESTAMP, TEST_DB_CONFIG, TEST_COLLECTION_PARAMS


class TestDataCollectionIntegration:
    """Integration tests for data collection."""
    
    @pytest.fixture
    async def storage(self) -> AsyncGenerator[DatabaseStorage, None]:
        """Create test database storage."""
        storage = DatabaseStorage(TEST_DB_CONFIG["dsn"])
        await storage.initialize()
        yield storage
        
        # Cleanup
        if storage._pool:
            async with storage._pool.acquire() as conn:
                await conn.execute("DROP TABLE IF EXISTS spray_events")
            await storage._pool.close()
    
    @pytest.fixture
    async def service(self, storage: DatabaseStorage) -> AsyncGenerator[DataCollectionService, None]:
        """Create test service."""
        service = DataCollectionService(storage)
        await service._start()
        yield service
        await service._stop()
    
    @pytest.mark.asyncio
    async def test_collection_workflow(self, service: DataCollectionService) -> None:
        """Test complete data collection workflow."""
        # 1. Start collection
        session = await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        assert session.sequence_id == TEST_SEQUENCE_ID
        
        # 2. Record multiple events
        events: List[SprayEvent] = []
        for i in range(3):
            event = SprayEvent(
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
            await service.record_spray_event(event)
            events.append(event)
        
        # 3. Retrieve events
        retrieved = await service.get_sequence_events(TEST_SEQUENCE_ID)
        assert len(retrieved) == 3
        assert all(isinstance(e, SprayEvent) for e in retrieved)
        assert [e.spray_index for e in retrieved] == [0, 1, 2]
        
        # 4. Stop collection
        await service.stop_collection()
        assert service.active_session is None
        
        # 5. Verify data persistence
        persisted = await service.get_sequence_events(TEST_SEQUENCE_ID)
        assert len(persisted) == 3
        assert all(
            e1.spray_index == e2.spray_index and
            e1.x_pos == e2.x_pos and
            e1.status == e2.status
            for e1, e2 in zip(events, persisted)
        )
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service: DataCollectionService) -> None:
        """Test error handling across components."""
        # Test database connection failures
        try:
            bad_storage = DatabaseStorage("postgresql://invalid:5432")
            await bad_storage.initialize()
            assert False, "Should have raised StorageError"
        except StorageError:
            pass
        
        # Test invalid data handling
        await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        
        # Try to record event with wrong sequence
        wrong_event = SprayEvent(
            sequence_id="wrong_sequence",
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
        
        with pytest.raises(DataCollectionError) as exc_info:
            await service.record_spray_event(wrong_event)
        assert "Event sequence ID does not match" in str(exc_info.value)
        
        # Try to start collection when one is already active
        with pytest.raises(DataCollectionError) as exc_info:
            await service.start_collection("another_sequence", TEST_COLLECTION_PARAMS)
        assert "Collection already in progress" in str(exc_info.value)
        
        # Stop collection and verify recovery
        await service.stop_collection()
        assert service.active_session is None
        
        # Should be able to start new collection
        session = await service.start_collection("new_sequence", TEST_COLLECTION_PARAMS)
        assert session.sequence_id == "new_sequence"
