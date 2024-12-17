"""Tests for data collection storage implementation."""

import datetime
from typing import AsyncGenerator
import pytest
import asyncpg
from asyncpg.pool import Pool

from micro_cold_spray.api.data_collection.storage import DatabaseStorage
from micro_cold_spray.api.data_collection.models import SprayEvent
from micro_cold_spray.api.data_collection.exceptions import StorageError

# Test database configuration
TEST_DB_NAME = "test_micro_cold_spray"
TEST_DB_USER = "postgres"
TEST_DB_PASS = "dbpassword"
TEST_DB_HOST = "localhost"
TEST_DB_PORT = "5432"

TEST_DSN = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASS}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"

# Test data
SAMPLE_EVENT = SprayEvent(
    sequence_id="test_sequence_1",
    spray_index=1,
    timestamp=datetime.datetime.now(datetime.timezone.utc),
    x_pos=1.0,
    y_pos=2.0,
    z_pos=3.0,
    pressure=100.0,
    temperature=25.0,
    flow_rate=5.0,
    status="completed"
)


@pytest.fixture
async def db_pool() -> AsyncGenerator[Pool, None]:
    """Create a database connection pool for testing."""
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
        await sys_conn.execute("COMMIT")
        # Terminate existing connections
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

    # Create connection pool to test database
    pool = await asyncpg.create_pool(TEST_DSN)
    yield pool
    
    # Close pool before cleanup
    await pool.close()

    # Clean up test database
    sys_conn = await asyncpg.connect(
        user=TEST_DB_USER,
        password=TEST_DB_PASS,
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        database="postgres"
    )
    try:
        await sys_conn.execute("COMMIT")
        # Terminate existing connections
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
async def storage(db_pool: Pool) -> AsyncGenerator[DatabaseStorage, None]:
    """Create a storage instance for testing."""
    storage = DatabaseStorage(TEST_DSN)
    await storage.initialize()
    yield storage
    if storage._pool:
        await storage._pool.close()


@pytest.fixture(autouse=True)
async def cleanup(db_pool: Pool) -> AsyncGenerator[None, None]:
    """Clean up the database after each test."""
    yield
    async with db_pool.acquire() as conn:
        # Check if tables exist before trying to truncate
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('spray_events', 'spray_runs')
        """)
        if tables:
            await conn.execute("TRUNCATE TABLE spray_events CASCADE;")
            await conn.execute("TRUNCATE TABLE spray_runs CASCADE;")


class TestDatabaseStorage:
    """Test database storage operations."""

    @pytest.mark.asyncio
    async def test_initialization(self, db_pool: Pool) -> None:
        """Test storage initialization creates required tables."""
        storage = DatabaseStorage(TEST_DSN)
        await storage.initialize()
        
        async with db_pool.acquire() as conn:
            # Check if tables exist
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('spray_runs', 'spray_events')
            """)
            assert len(tables) == 2
            
            # Check if indexes exist
            indexes = await conn.fetch("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename IN ('spray_runs', 'spray_events')
            """)
            assert len(indexes) >= 2  # At least our basic indexes

    @pytest.mark.asyncio
    async def test_save_spray_event(self, storage: DatabaseStorage) -> None:
        """Test saving a spray event."""
        await storage.save_spray_event(SAMPLE_EVENT)
        events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
        
        assert len(events) == 1
        event = events[0]
        assert event.sequence_id == SAMPLE_EVENT.sequence_id
        assert event.spray_index == SAMPLE_EVENT.spray_index
        assert event.x_pos == SAMPLE_EVENT.x_pos
        assert event.y_pos == SAMPLE_EVENT.y_pos
        assert event.z_pos == SAMPLE_EVENT.z_pos
        assert event.pressure == SAMPLE_EVENT.pressure
        assert event.temperature == SAMPLE_EVENT.temperature
        assert event.flow_rate == SAMPLE_EVENT.flow_rate
        assert event.status == SAMPLE_EVENT.status

    @pytest.mark.asyncio
    async def test_save_duplicate_event(self, storage: DatabaseStorage) -> None:
        """Test saving a duplicate spray event."""
        await storage.save_spray_event(SAMPLE_EVENT)
        with pytest.raises(StorageError) as exc_info:
            await storage.save_spray_event(SAMPLE_EVENT)
        assert "Duplicate spray event" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_spray_event(self, storage: DatabaseStorage) -> None:
        """Test updating a spray event."""
        await storage.save_spray_event(SAMPLE_EVENT)
        events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
        event_id = events[0].id

        updated_event = SAMPLE_EVENT.model_copy(update={"status": "error"})
        await storage.update_spray_event(event_id, updated_event)

        events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
        assert events[0].status == "error"

    @pytest.mark.asyncio
    async def test_get_nonexistent_events(self, storage: DatabaseStorage) -> None:
        """Test getting events for nonexistent sequence."""
        events = await storage.get_spray_events("nonexistent_sequence")
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_invalid_connection(self) -> None:
        """Test initialization with invalid connection string."""
        storage = DatabaseStorage("postgresql://invalid:5432/nonexistent")
        with pytest.raises(StorageError) as exc_info:
            await storage.initialize()
        assert "Failed to initialize database" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_basic_transaction(self, storage: DatabaseStorage, db_pool: Pool) -> None:
        """Test basic transaction handling."""
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Save event within transaction
                await storage.save_spray_event(SAMPLE_EVENT)
                
                # Verify event is saved
                events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
                assert len(events) == 1
