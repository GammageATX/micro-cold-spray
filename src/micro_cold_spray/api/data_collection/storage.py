"""Database storage implementation for spray events."""

from typing import List, Protocol
import asyncpg
from loguru import logger

from .models import SprayEvent
from .exceptions import StorageError


class DataStorage(Protocol):
    """Protocol for data storage implementations."""
    
    async def initialize(self) -> None:
        """Initialize storage (create tables etc)."""
        ...
    
    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save a spray event."""
        ...
    
    async def update_spray_event(self, event: SprayEvent) -> None:
        """Update an existing spray event."""
        ...
    
    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence."""
        ...


class DatabaseStorage:
    """PostgreSQL/TimescaleDB storage implementation."""
    
    def __init__(self, dsn: str):
        """Initialize with database connection string."""
        self._dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        """Initialize database connection pool and tables."""
        try:
            self._pool = await asyncpg.create_pool(self._dsn)
            
            # Create tables if they don't exist
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS spray_events (
                        id SERIAL PRIMARY KEY,
                        sequence_id TEXT NOT NULL,
                        spray_index INTEGER NOT NULL,
                        timestamp TIMESTAMPTZ NOT NULL,
                        x_pos FLOAT NOT NULL,
                        y_pos FLOAT NOT NULL,
                        z_pos FLOAT NOT NULL,
                        pressure FLOAT NOT NULL,
                        temperature FLOAT NOT NULL,
                        flow_rate FLOAT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(sequence_id, spray_index)
                    );

                    -- Create index on sequence_id for faster lookups
                    CREATE INDEX IF NOT EXISTS idx_spray_events_sequence_id
                        ON spray_events(sequence_id);

                    -- Create index on timestamp for time-based queries
                    CREATE INDEX IF NOT EXISTS idx_spray_events_timestamp
                        ON spray_events(timestamp);
                """)

                # Try to create TimescaleDB extension if available
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                    logger.info("TimescaleDB extension created successfully")
                except asyncpg.exceptions.FeatureNotSupportedError:
                    logger.warning("TimescaleDB extension not available - continuing without time-series optimization")

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise StorageError("Failed to initialize database", {"error": str(e)})

    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save spray event to database."""
        if not self._pool:
            raise StorageError("Database not initialized")

        try:
            # Validate field values
            if not all(isinstance(val, (int, float)) and -1e308 <= val <= 1e308 for val in [
                event.x_pos, event.y_pos, event.z_pos,
                event.pressure, event.temperature, event.flow_rate
            ]):
                raise StorageError("Failed to save spray event", {
                    "error": "Field values out of range",
                    "fields": {
                        "x_pos": event.x_pos,
                        "y_pos": event.y_pos,
                        "z_pos": event.z_pos,
                        "pressure": event.pressure,
                        "temperature": event.temperature,
                        "flow_rate": event.flow_rate
                    }
                })

            async with self._pool.acquire() as conn:
                try:
                    result = await conn.fetchrow(
                        """
                        INSERT INTO spray_events (
                            sequence_id,
                            spray_index,
                            timestamp,
                            x_pos,
                            y_pos,
                            z_pos,
                            pressure,
                            temperature,
                            flow_rate,
                            status
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        RETURNING id
                        """,
                        event.sequence_id, event.spray_index, event.timestamp,
                        event.x_pos, event.y_pos, event.z_pos,
                        event.pressure, event.temperature, event.flow_rate,
                        event.status
                    )
                    event.id = result['id']
                    logger.debug(f"Saved spray event {event.spray_index} to database")
                except asyncpg.exceptions.UniqueViolationError:
                    logger.error(f"Duplicate spray event: {event.spray_index}")
                    raise StorageError("Duplicate spray event", {
                        "sequence_id": event.sequence_id,
                        "spray_index": event.spray_index
                    })
        except StorageError:
            raise
        except Exception as e:
            logger.error(f"Failed to save spray event: {str(e)}")
            raise StorageError("Failed to save spray event", {"error": str(e)})

    async def update_spray_event(self, event_id: int, event: SprayEvent) -> None:
        """Update a spray event in the database."""
        if not self._pool:
            raise StorageError("Database not initialized")

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE spray_events
                    SET sequence_id = $1,
                        spray_index = $2,
                        timestamp = $3,
                        x_pos = $4,
                        y_pos = $5,
                        z_pos = $6,
                        pressure = $7,
                        temperature = $8,
                        flow_rate = $9,
                        status = $10
                    WHERE id = $11
                    """,
                    event.sequence_id, event.spray_index, event.timestamp,
                    event.x_pos, event.y_pos, event.z_pos,
                    event.pressure, event.temperature, event.flow_rate,
                    event.status, event_id
                )

                if result == "UPDATE 0":
                    raise StorageError("Spray event not found", {"event_id": event_id})

                logger.debug(f"Updated spray event {event_id} in database")
        except StorageError:
            raise
        except Exception as e:
            logger.error(f"Failed to update spray event: {str(e)}")
            raise StorageError("Failed to update spray event", {"error": str(e)})

    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence."""
        if not self._pool:
            raise StorageError("Database not initialized")

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, sequence_id, spray_index, timestamp,
                           x_pos, y_pos, z_pos,
                           pressure, temperature, flow_rate,
                           status
                    FROM spray_events
                    WHERE sequence_id = $1
                    ORDER BY spray_index;
                    """,
                    sequence_id
                )

                return [SprayEvent(
                    id=row['id'],
                    sequence_id=row['sequence_id'],
                    spray_index=row['spray_index'],
                    timestamp=row['timestamp'],
                    x_pos=row['x_pos'],
                    y_pos=row['y_pos'],
                    z_pos=row['z_pos'],
                    pressure=row['pressure'],
                    temperature=row['temperature'],
                    flow_rate=row['flow_rate'],
                    status=row['status']
                ) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get spray events: {str(e)}")
            raise StorageError("Failed to get spray events", {"error": str(e)})
