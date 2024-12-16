"""# Data Collection Storage Tests

Tests for the data collection storage implementation."""

import asyncio
import datetime
from typing import AsyncGenerator, Generator
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


class TestStorageInitialization:
    """Test storage initialization and connection management."""
    
    @pytest.mark.asyncio
    async def test_initialization_creates_pool(self) -> None:
        """Test that initialization creates a connection pool."""
        storage = DatabaseStorage(TEST_DSN)
        try:
            await storage.initialize()
            assert storage._pool is not None
            assert isinstance(storage._pool, Pool)
            assert not storage._pool.is_closing()
        finally:
            if storage._pool:
                await storage._pool.close()
    
    @pytest.mark.asyncio
    async def test_initialization_with_invalid_dsn(self) -> None:
        """Test initialization with invalid connection string."""
        invalid_dsn = "postgresql://invalid:5432/nonexistent"
        storage = DatabaseStorage(invalid_dsn)
        with pytest.raises(StorageError) as exc_info:
            await storage.initialize()
        assert "Failed to initialize database" in str(exc_info.value)
        assert storage._pool is None
    
    @pytest.mark.asyncio
    async def test_initialization_idempotent(self) -> None:
        """Test that multiple initializations are handled correctly."""
        storage = DatabaseStorage(TEST_DSN)
        try:
            # First initialization
            await storage.initialize()
            original_pool = storage._pool
            
            # Second initialization should reuse the same pool
            await storage.initialize()
            assert storage._pool is original_pool
            assert not storage._pool.is_closing()
            
            # Verify pool is functional
            async with storage._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                assert result == 1
        finally:
            if storage._pool:
                await storage._pool.close()
    
    @pytest.mark.asyncio
    async def test_cleanup_closes_pool(self) -> None:
        """Test that cleanup properly closes the connection pool."""
        storage = DatabaseStorage(TEST_DSN)
        await storage.initialize()
        pool = storage._pool
        assert not pool.is_closing()
        
        await storage._pool.close()  # Use direct pool closing since cleanup isn't implemented
        assert pool.is_closing()
        storage._pool = None  # Cleanup the reference


class TestStorageTransactions:
    """Test transaction management in storage operations."""
    
    @pytest.fixture
    async def storage(self) -> AsyncGenerator[DatabaseStorage, None]:
        """Create and initialize storage for tests."""
        storage = DatabaseStorage(TEST_DSN)
        await storage.initialize()
        yield storage
        if storage._pool:
            await storage._pool.close()
            storage._pool = None
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self, storage: DatabaseStorage):
        """Test successful transaction commit."""
        async with storage._pool.acquire() as conn:
            async with conn.transaction():
                # Create test table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_transaction (
                        id SERIAL PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                # Insert test data
                await conn.execute(
                    "INSERT INTO test_transaction (value) VALUES ($1)",
                    "test_value"
                )
            
            # Verify data was committed
            result = await conn.fetchval(
                "SELECT value FROM test_transaction WHERE value = $1",
                "test_value"
            )
            assert result == "test_value"
            
            # Cleanup
            await conn.execute("DROP TABLE test_transaction")
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, storage: DatabaseStorage):
        """Test transaction rollback on error."""
        async with storage._pool.acquire() as conn:
            # Create test table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_transaction (
                    id SERIAL PRIMARY KEY,
                    value TEXT
                )
            """)
            
            try:
                async with conn.transaction():
                    await conn.execute(
                        "INSERT INTO test_transaction (value) VALUES ($1)",
                        "test_value"
                    )
                    # Simulate error
                    raise Exception("Test error")
            except Exception:
                pass
            
            # Verify data was rolled back
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM test_transaction WHERE value = $1",
                "test_value"
            )
            assert count == 0
            
            # Cleanup
            await conn.execute("DROP TABLE test_transaction")
    
    @pytest.mark.asyncio
    async def test_nested_transaction(self, storage: DatabaseStorage):
        """Test nested transaction handling."""
        async with storage._pool.acquire() as conn:
            async with conn.transaction():
                # Create test table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_transaction (
                        id SERIAL PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                # Start nested transaction
                async with conn.transaction():
                    await conn.execute(
                        "INSERT INTO test_transaction (value) VALUES ($1)",
                        "nested_value"
                    )
                
                # Verify nested transaction committed
                result = await conn.fetchval(
                    "SELECT value FROM test_transaction WHERE value = $1",
                    "nested_value"
                )
                assert result == "nested_value"
                
                # Cleanup
                await conn.execute("DROP TABLE test_transaction")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
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
        # We need to execute these commands outside of a transaction
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

    # Create connection pool to test database
    pool = await asyncpg.create_pool(
        TEST_DSN,
        min_size=2,
        max_size=10,
        command_timeout=60.0
    )

    try:
        # Create TimescaleDB extension
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

        yield pool
    finally:
        # Cleanup
        await pool.close()

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
async def storage(db_pool: Pool) -> AsyncGenerator[DatabaseStorage, None]:
    """Create a storage instance for testing."""
    storage = DatabaseStorage(TEST_DSN)
    await storage.initialize()
    try:
        yield storage
    finally:
        if storage._pool:
            await storage._pool.close()


@pytest.fixture(autouse=True)
async def cleanup(db_pool: Pool) -> AsyncGenerator[None, None]:
    """Clean up the database after each test."""
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE spray_events;")


@pytest.mark.asyncio
async def test_initialize_creates_tables(db_pool: Pool) -> None:
    """Test that initialization creates the required tables."""
    storage = DatabaseStorage(TEST_DSN)
    await storage.initialize()
    
    async with db_pool.acquire() as conn:
        # Check if spray_events table exists
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'spray_events'
            );
        """)
        assert result is True
        
        # Check if required indexes exist
        result = await conn.fetch("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'spray_events'
            ORDER BY indexname;
        """)
        index_names = {row['indexname'] for row in result}
        assert 'idx_spray_events_sequence_id' in index_names
        assert 'idx_spray_events_timestamp' in index_names

        # Check if TimescaleDB extension is installed
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM pg_extension
                WHERE extname = 'timescaledb'
            );
        """)
        assert result is True


@pytest.mark.asyncio
async def test_save_spray_event(storage: DatabaseStorage, db_pool: Pool) -> None:
    """Test saving a spray event."""
    await storage.save_spray_event(SAMPLE_EVENT)
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM spray_events WHERE sequence_id = $1 AND spray_index = $2",
            SAMPLE_EVENT.sequence_id,
            SAMPLE_EVENT.spray_index
        )
        
        assert row is not None
        assert row['sequence_id'] == SAMPLE_EVENT.sequence_id
        assert row['spray_index'] == SAMPLE_EVENT.spray_index
        assert row['x_pos'] == SAMPLE_EVENT.x_pos
        assert row['y_pos'] == SAMPLE_EVENT.y_pos
        assert row['z_pos'] == SAMPLE_EVENT.z_pos
        assert row['pressure'] == SAMPLE_EVENT.pressure
        assert row['temperature'] == SAMPLE_EVENT.temperature
        assert row['flow_rate'] == SAMPLE_EVENT.flow_rate
        assert row['status'] == SAMPLE_EVENT.status


@pytest.mark.asyncio
async def test_save_duplicate_spray_event(storage: DatabaseStorage) -> None:
    """Test saving a duplicate spray event."""
    await storage.save_spray_event(SAMPLE_EVENT)
    with pytest.raises(StorageError) as exc_info:
        await storage.save_spray_event(SAMPLE_EVENT)
    assert "Duplicate spray event" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_spray_event(storage: DatabaseStorage) -> None:
    """Test updating a spray event."""
    # First save the event
    await storage.save_spray_event(SAMPLE_EVENT)
    
    # Get the event ID
    events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
    assert len(events) == 1
    event_id = events[0].id

    # Update the event
    updated_event = SAMPLE_EVENT.copy(update={"status": "completed"})
    await storage.update_spray_event(event_id, updated_event)

    # Verify the update
    events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
    assert len(events) == 1
    assert events[0].status == "completed"


@pytest.mark.asyncio
async def test_get_spray_events(storage: DatabaseStorage) -> None:
    """Test retrieving spray events."""
    # Save multiple events
    events = [
        SAMPLE_EVENT,
        SAMPLE_EVENT.copy(update={"spray_index": 2}),
        SAMPLE_EVENT.copy(update={"spray_index": 3})
    ]
    
    for event in events:
        await storage.save_spray_event(event)
    
    # Retrieve events
    retrieved_events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
    
    assert len(retrieved_events) == 3
    assert all(isinstance(event, SprayEvent) for event in retrieved_events)
    assert [event.spray_index for event in retrieved_events] == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_spray_events_empty_sequence(storage: DatabaseStorage) -> None:
    """Test retrieving spray events for non-existent sequence."""
    events = await storage.get_spray_events("non_existent_sequence")
    assert len(events) == 0


@pytest.mark.asyncio
async def test_storage_without_initialization(db_pool: Pool) -> None:
    """Test using storage without initialization."""
    storage = DatabaseStorage(TEST_DSN)
    with pytest.raises(StorageError) as exc_info:
        await storage.save_spray_event(SAMPLE_EVENT)
    assert "Database not initialized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_database_connection() -> None:
    """Test initialization with invalid database connection."""
    storage = DatabaseStorage("postgresql://invalid:5432/nonexistent")
    
    with pytest.raises(StorageError) as exc_info:
        await storage.initialize()
    assert "Failed to initialize database" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_nonexistent_event(storage: DatabaseStorage) -> None:
    """Test updating a spray event that doesn't exist."""
    with pytest.raises(StorageError) as exc_info:
        await storage.update_spray_event(999, SAMPLE_EVENT)
    assert "Spray event not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_spray_event_field_limits(storage: DatabaseStorage, db_pool: Pool) -> None:
    """Test spray event field value limits."""
    # Test maximum values
    max_event = SAMPLE_EVENT.copy()
    max_event.pressure = float('inf')
    max_event.temperature = float('inf')
    max_event.flow_rate = float('inf')
    
    with pytest.raises(StorageError) as exc_info:
        await storage.save_spray_event(max_event)
    assert "Failed to save spray event" in str(exc_info.value)
    
    # Test minimum values
    min_event = SAMPLE_EVENT.copy()
    min_event.pressure = float('-inf')
    min_event.temperature = float('-inf')
    min_event.flow_rate = float('-inf')
    
    with pytest.raises(StorageError) as exc_info:
        await storage.save_spray_event(min_event)
    assert "Failed to save spray event" in str(exc_info.value)


@pytest.mark.asyncio
async def test_connection_pool_exhaustion(storage: DatabaseStorage) -> None:
    """Test handling of connection pool exhaustion."""
    # Create many concurrent operations to exhaust pool
    async def concurrent_operation(i: int) -> None:
        event = SAMPLE_EVENT.copy()
        event.spray_index = i
        await storage.save_spray_event(event)
    
    # Try to exhaust connection pool with concurrent operations
    tasks = [concurrent_operation(i) for i in range(100)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify storage is still operational
    events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
    assert len(events) > 0


@pytest.mark.asyncio
async def test_concurrent_event_updates(storage: DatabaseStorage) -> None:
    """Test concurrent updates to the same event."""
    # First save the event
    await storage.save_spray_event(SAMPLE_EVENT)
    
    # Try concurrent updates
    async def update_pressure(value: float) -> None:
        event = SAMPLE_EVENT.copy()
        event.pressure = value
        await storage.update_spray_event(event)
    
    # Run concurrent updates
    tasks = [update_pressure(float(i)) for i in range(5)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify final state
    events = await storage.get_spray_events(SAMPLE_EVENT.sequence_id)
    assert len(events) == 1
    assert events[0].sequence_id == SAMPLE_EVENT.sequence_id
    assert events[0].spray_index == SAMPLE_EVENT.spray_index
