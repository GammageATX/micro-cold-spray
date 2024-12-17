"""Integration tests for data collection API."""

import pytest
import asyncpg
from typing import AsyncGenerator, List
from datetime import datetime, timezone
from pydantic import ValidationError

from micro_cold_spray.api.data_collection.storage import DatabaseStorage
from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError, StorageError
from micro_cold_spray.api.base.exceptions import ServiceError
from . import TEST_SEQUENCE_ID, TEST_TIMESTAMP, TEST_DB_CONFIG, TEST_COLLECTION_PARAMS
from .test_data_storage import TEST_DB_USER, TEST_DB_PASS, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME


class TestDataCollectionIntegration:
    """Integration tests for data collection."""
    
    @pytest.fixture
    async def storage(self) -> AsyncGenerator[DatabaseStorage, None]:
        """Create test database storage."""
        # Connect to default database to create test database
        sys_conn = await asyncpg.connect(
            user=TEST_DB_USER,
            password=TEST_DB_PASS,
            host=TEST_DB_HOST,
            port=TEST_DB_PORT,
            database="postgres"
        )

        try:
            # Drop test database if it exists and create it fresh
            await sys_conn.execute("COMMIT")  # Exit any transaction
            await sys_conn.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
                AND pid <> pg_backend_pid();
            """)
            await sys_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
            await sys_conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
        finally:
            await sys_conn.close()

        # Initialize storage
        storage = DatabaseStorage(TEST_DB_CONFIG["dsn"])
        await storage.initialize()
        yield storage
        
        # Cleanup
        if storage._pool:
            async with storage._pool.acquire() as conn:
                await conn.execute("DROP TABLE IF EXISTS spray_events")
            await storage._pool.close()

        # Drop test database
        sys_conn = await asyncpg.connect(
            user=TEST_DB_USER,
            password=TEST_DB_PASS,
            host=TEST_DB_HOST,
            port=TEST_DB_PORT,
            database="postgres"
        )
        try:
            await sys_conn.execute("COMMIT")  # Exit any transaction
            await sys_conn.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
                AND pid <> pg_backend_pid();
            """)
            await sys_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        finally:
            await sys_conn.close()
    
    @pytest.fixture
    async def service(self, storage: DatabaseStorage) -> AsyncGenerator[DataCollectionService, None]:
        """Create test service."""
        service = DataCollectionService(storage)
        await service.start()  # Start the service
        yield service
        await service.stop()  # Stop the service
    
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

    @pytest.mark.asyncio
    async def test_service_lifecycle_errors(self, storage: DatabaseStorage) -> None:
        """Test service lifecycle error handling."""
        service = DataCollectionService(storage)
        
        # Test operations before start
        with pytest.raises(DataCollectionError) as exc_info:
            await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        assert "Service not running" in str(exc_info.value)
        
        # Start service
        await service.start()
        assert service.is_running
        
        # Test double start
        with pytest.raises(ServiceError) as exc_info:
            await service.start()
        assert "already running" in str(exc_info.value)
        
        # Stop service
        await service.stop()
        assert not service.is_running
        
        # Test operations after stop
        with pytest.raises(DataCollectionError) as exc_info:
            await service.get_sequence_events(TEST_SEQUENCE_ID)
        assert "Service not running" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_event_validation(self, service: DataCollectionService) -> None:
        """Test spray event validation and error handling."""
        await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        
        # Test event with invalid values
        with pytest.raises(ValidationError) as exc_info:
            SprayEvent(
                sequence_id=TEST_SEQUENCE_ID,
                spray_index=-1,  # Invalid negative index
                timestamp=TEST_TIMESTAMP,
                x_pos=float('inf'),  # Invalid position
                y_pos=0.0,
                z_pos=0.0,
                pressure=-100.0,  # Invalid negative pressure
                temperature=1000.0,  # Invalid high temperature
                flow_rate=0.0,
                status="invalid_status"  # Invalid status
            )
        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)  # spray_index
        assert any("finite number" in str(e["msg"]) for e in errors)  # x_pos
        assert any("greater than 0" in str(e["msg"]) for e in errors)  # pressure
        assert any("Input should be 'active', 'completed', 'error' or 'paused'" in str(e["msg"]) for e in errors)  # status
        
        # Test event with future timestamp
        future_time = datetime.now(timezone.utc).replace(year=2050)
        with pytest.raises(ValidationError) as exc_info:
            SprayEvent(
                sequence_id=TEST_SEQUENCE_ID,
                spray_index=0,
                timestamp=future_time,
                x_pos=0.0,
                y_pos=0.0,
                z_pos=0.0,
                pressure=100.0,
                temperature=25.0,
                flow_rate=5.0,
                status="active"
            )
        assert "Timestamp cannot be in the future" in str(exc_info.value)
        
        # Test duplicate spray index
        event1 = SprayEvent(
            sequence_id=TEST_SEQUENCE_ID,
            spray_index=1,
            timestamp=TEST_TIMESTAMP,
            x_pos=0.0,
            y_pos=0.0,
            z_pos=0.0,
            pressure=100.0,
            temperature=25.0,
            flow_rate=5.0,
            status="active"
        )
        await service.record_spray_event(event1)
        
        with pytest.raises(DataCollectionError) as exc_info:
            await service.record_spray_event(event1)  # Same event again
        assert "Failed to record spray event" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, service: DataCollectionService) -> None:
        """Test concurrent data collection operations."""
        await service.start_collection(TEST_SEQUENCE_ID, TEST_COLLECTION_PARAMS)
        
        # Create multiple events concurrently
        async def record_event(index: int) -> None:
            event = SprayEvent(
                sequence_id=TEST_SEQUENCE_ID,
                spray_index=index,
                timestamp=TEST_TIMESTAMP,
                x_pos=float(index),
                y_pos=float(index),
                z_pos=float(index),
                pressure=100.0,
                temperature=25.0,
                flow_rate=5.0,
                status="active"
            )
            await service.record_spray_event(event)
        
        # Record 10 events concurrently
        import asyncio
        tasks = [record_event(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all events were recorded
        events = await service.get_sequence_events(TEST_SEQUENCE_ID)
        assert len(events) == 10
        assert sorted([e.spray_index for e in events]) == list(range(10))
        
        # Test concurrent reads
        async def get_events() -> List[SprayEvent]:
            return await service.get_sequence_events(TEST_SEQUENCE_ID)
        
        # Perform multiple concurrent reads
        read_tasks = [get_events() for _ in range(5)]
        results = await asyncio.gather(*read_tasks)
        
        # Verify all reads return the same data
        assert all(len(events) == 10 for events in results)
        assert all(
            sorted([e.spray_index for e in events]) == list(range(10))
            for events in results
        )
