"""Database storage implementation for spray events."""

import logging
from typing import List, Protocol
import asyncpg

from .service import SprayEvent

logger = logging.getLogger(__name__)


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
                    
                    -- Create TimescaleDB hypertable
                    SELECT create_hypertable('spray_events', 'timestamp',
                        if_not_exists => TRUE);
                    
                    -- Create index on sequence_id for faster lookups
                    CREATE INDEX IF NOT EXISTS idx_spray_events_sequence_id
                        ON spray_events(sequence_id);
                """)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save spray event to database."""
        if not self._pool:
            raise RuntimeError("Database not initialized")
            
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO spray_events (
                        sequence_id, spray_index, timestamp,
                        x_pos, y_pos, z_pos,
                        pressure, temperature, flow_rate,
                        status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    event.sequence_id,
                    event.spray_index,
                    event.timestamp,
                    event.x_pos,
                    event.y_pos,
                    event.z_pos,
                    event.pressure,
                    event.temperature,
                    event.flow_rate,
                    event.status
                )
                logger.debug(f"Saved spray event {event.spray_index} to database")
        except asyncpg.UniqueViolationError:
            logger.warning(f"Spray event already exists: {event.sequence_id}/{event.spray_index}")
        except Exception as e:
            logger.error(f"Failed to save spray event: {str(e)}")
            raise

    async def update_spray_event(self, event: SprayEvent) -> None:
        """Update spray event in database."""
        if not self._pool:
            raise RuntimeError("Database not initialized")
            
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE spray_events SET
                        timestamp = $3,
                        x_pos = $4,
                        y_pos = $5,
                        z_pos = $6,
                        pressure = $7,
                        temperature = $8,
                        flow_rate = $9,
                        status = $10
                    WHERE sequence_id = $1 AND spray_index = $2
                    """,
                    event.sequence_id,
                    event.spray_index,
                    event.timestamp,
                    event.x_pos,
                    event.y_pos,
                    event.z_pos,
                    event.pressure,
                    event.temperature,
                    event.flow_rate,
                    event.status
                )
                logger.debug(f"Updated spray event {event.spray_index} in database")
        except Exception as e:
            logger.error(f"Failed to update spray event: {str(e)}")
            raise

    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get spray events from database."""
        if not self._pool:
            raise RuntimeError("Database not initialized")
            
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM spray_events
                    WHERE sequence_id = $1
                    ORDER BY spray_index ASC
                """, sequence_id)
                
                return [
                    SprayEvent(
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
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get spray events: {str(e)}")
            raise
