"""Tests for data collection storage."""

import pytest

from micro_cold_spray.api.data_collection.storage import DatabaseStorage
from micro_cold_spray.api.data_collection.models import SprayEvent
from micro_cold_spray.api.data_collection.exceptions import StorageError
from . import TEST_SEQUENCE_ID, TEST_TIMESTAMP, TEST_DB_CONFIG


class TestDatabaseStorage:
    """Test database storage implementation."""
    
    @pytest.fixture
    async def db_storage(self):
        """Create test database storage instance."""
        storage = DatabaseStorage(TEST_DB_CONFIG["dsn"])
        await storage.initialize()
        yield storage
        
        # Cleanup tables after tests
        if storage._pool:
            async with storage._pool.acquire() as conn:
                await conn.execute("DROP TABLE IF EXISTS spray_events")
            await storage._pool.close()
    
    async def test_initialize_db(self, db_storage):
        """Test database initialization."""
        # Verify connection pool exists
        assert db_storage._pool is not None
        
        # Verify tables exist
        async with db_storage._pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'spray_events'
                )
            """)
            assert result is True
            
            # Verify indexes exist
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE tablename = 'spray_events'
                    AND indexname = 'idx_spray_events_sequence_id'
                )
            """)
            assert result is True
    
    async def test_save_spray_event(self, db_storage):
        """Test saving spray event."""
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
        
        # Test successful save
        await db_storage.save_spray_event(event)
        
        # Verify saved data
        async with db_storage._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM spray_events WHERE sequence_id = $1 AND spray_index = $2",
                TEST_SEQUENCE_ID, 1
            )
            assert row is not None
            assert row['x_pos'] == 10.0
            assert row['status'] == "active"
        
        # Test duplicate event handling
        with pytest.raises(StorageError) as exc_info:
            await db_storage.save_spray_event(event)
        assert "Spray event already exists" in str(exc_info.value)
    
    async def test_update_spray_event(self, db_storage):
        """Test updating spray event."""
        # Create initial event
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
        await db_storage.save_spray_event(event)
        
        # Update event
        updated_event = SprayEvent(
            sequence_id=TEST_SEQUENCE_ID,
            spray_index=1,
            timestamp=TEST_TIMESTAMP,
            x_pos=15.0,  # Changed
            y_pos=25.0,  # Changed
            z_pos=35.0,  # Changed
            pressure=100.0,
            temperature=25.0,
            flow_rate=5.0,
            status="completed"  # Changed
        )
        await db_storage.update_spray_event(updated_event)
        
        # Verify updated data
        async with db_storage._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM spray_events WHERE sequence_id = $1 AND spray_index = $2",
                TEST_SEQUENCE_ID, 1
            )
            assert row['x_pos'] == 15.0
            assert row['y_pos'] == 25.0
            assert row['z_pos'] == 35.0
            assert row['status'] == "completed"
    
    async def test_get_spray_events(self, db_storage):
        """Test retrieving spray events."""
        # Create test events
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
        
        for event in events:
            await db_storage.save_spray_event(event)
        
        # Test getting events for sequence
        retrieved_events = await db_storage.get_spray_events(TEST_SEQUENCE_ID)
        assert len(retrieved_events) == 3
        assert all(isinstance(e, SprayEvent) for e in retrieved_events)
        assert [e.spray_index for e in retrieved_events] == [0, 1, 2]
        
        # Test empty sequence
        empty_events = await db_storage.get_spray_events("non_existent")
        assert len(empty_events) == 0
