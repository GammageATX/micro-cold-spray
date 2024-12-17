"""Database storage implementation for spray events."""

from typing import List, Protocol
import json
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
    """PostgreSQL storage implementation."""
    
    def __init__(self, dsn: str):
        """Initialize with database connection string."""
        self._dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        """Initialize database connection and schema."""
        if self._pool and not self._pool.is_closing():
            logger.debug("Reusing existing connection pool")
            return
        
        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=2,
                max_size=10,
                command_timeout=60.0
            )
            
            # Create tables if they don't exist
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS spray_runs (
                        id SERIAL PRIMARY KEY,
                        sequence_id TEXT NOT NULL,
                        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        end_time TIMESTAMP WITH TIME ZONE,
                        operator TEXT,
                        nozzle_type TEXT,
                        powder_type TEXT,
                        parameters JSONB,
                        status TEXT NOT NULL,
                        error TEXT,
                        UNIQUE(sequence_id)
                    );

                    CREATE TABLE IF NOT EXISTS spray_events (
                        id SERIAL PRIMARY KEY,
                        run_id INTEGER REFERENCES spray_runs(id),
                        spray_index INTEGER NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        position JSONB NOT NULL,
                        measurements JSONB NOT NULL,
                        status TEXT NOT NULL,
                        UNIQUE(run_id, spray_index)
                    );

                    -- Basic indexes
                    CREATE INDEX IF NOT EXISTS idx_spray_runs_sequence_id
                    ON spray_runs(sequence_id);
                    
                    CREATE INDEX IF NOT EXISTS idx_spray_events_run_id
                    ON spray_events(run_id);
                """)
                
            logger.info("Database initialized successfully")
            
        except Exception as e:
            if self._pool:
                await self._pool.close()
                self._pool = None
            raise StorageError(f"Failed to initialize database: {str(e)}")

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
                # Get or create run record
                run_id = await conn.fetchval("""
                    SELECT id FROM spray_runs
                    WHERE sequence_id = $1
                """, event.sequence_id)

                if not run_id:
                    run_id = await conn.fetchval("""
                        INSERT INTO spray_runs (
                            sequence_id, start_time, status
                        ) VALUES ($1, $2, 'active')
                        RETURNING id
                    """, event.sequence_id, event.timestamp)

                # Insert event
                try:
                    position = json.dumps({
                        "x": event.x_pos,
                        "y": event.y_pos,
                        "z": event.z_pos
                    })
                    measurements = json.dumps({
                        "pressure": event.pressure,
                        "temperature": event.temperature,
                        "flow_rate": event.flow_rate
                    })
                    
                    result = await conn.fetchrow(
                        """
                        INSERT INTO spray_events (
                            run_id,
                            spray_index,
                            timestamp,
                            position,
                            measurements,
                            status
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        RETURNING id
                        """,
                        run_id,
                        event.spray_index,
                        event.timestamp,
                        position,
                        measurements,
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
                position = json.dumps({
                    "x": event.x_pos,
                    "y": event.y_pos,
                    "z": event.z_pos
                })
                measurements = json.dumps({
                    "pressure": event.pressure,
                    "temperature": event.temperature,
                    "flow_rate": event.flow_rate
                })
                
                result = await conn.execute(
                    """
                    UPDATE spray_events
                    SET timestamp = $1,
                        position = $2,
                        measurements = $3,
                        status = $4
                    WHERE id = $5
                    """,
                    event.timestamp,
                    position,
                    measurements,
                    event.status,
                    event_id
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
                run = await conn.fetchrow(
                    """
                    SELECT id FROM spray_runs
                    WHERE sequence_id = $1
                    """,
                    sequence_id
                )
                
                if not run:
                    return []

                rows = await conn.fetch(
                    """
                    SELECT id, spray_index, timestamp,
                           position->>'x' as x_pos,
                           position->>'y' as y_pos,
                           position->>'z' as z_pos,
                           measurements->>'pressure' as pressure,
                           measurements->>'temperature' as temperature,
                           measurements->>'flow_rate' as flow_rate,
                           status
                    FROM spray_events
                    WHERE run_id = $1
                    ORDER BY spray_index;
                    """,
                    run['id']
                )

                return [SprayEvent(
                    id=row['id'],
                    sequence_id=sequence_id,
                    spray_index=row['spray_index'],
                    timestamp=row['timestamp'],
                    x_pos=float(row['x_pos']),
                    y_pos=float(row['y_pos']),
                    z_pos=float(row['z_pos']),
                    pressure=float(row['pressure']),
                    temperature=float(row['temperature']),
                    flow_rate=float(row['flow_rate']),
                    status=row['status']
                ) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get spray events: {str(e)}")
            raise StorageError("Failed to get spray events", {"error": str(e)})
