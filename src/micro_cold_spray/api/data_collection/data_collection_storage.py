"""Database storage implementation for spray events."""

from typing import List, Protocol, Dict, Any
import json
import asyncpg
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from .data_collection_models import SprayEvent


class DataStorage(Protocol):
    """Protocol for data storage implementations."""
    
    async def initialize(self) -> None:
        """Initialize storage (create tables etc).
        
        Raises:
            HTTPException: If initialization fails
        """
        ...
    
    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save a spray event.
        
        Raises:
            HTTPException: If save fails
        """
        ...
    
    async def update_spray_event(self, event: SprayEvent) -> None:
        """Update an existing spray event.
        
        Raises:
            HTTPException: If update fails
        """
        ...
    
    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence.
        
        Raises:
            HTTPException: If retrieval fails
        """
        ...
        
    async def check_connection(self) -> bool:
        """Check database connection.
        
        Returns:
            True if connection is healthy
        """
        ...
        
    async def check_storage(self) -> bool:
        """Check storage functionality.
        
        Returns:
            True if storage is working properly
        """
        ...
        
    async def check_health(self) -> Dict[str, Any]:
        """Check storage health.
        
        Returns:
            Health status information
            
        Raises:
            HTTPException: If health check fails
        """
        ...


class DatabaseStorage:
    """PostgreSQL storage implementation."""
    
    def __init__(self, dsn: str):
        """Initialize with database connection string."""
        self._dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        """Initialize database connection and schema.
        
        Raises:
            HTTPException: If initialization fails
        """
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
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize database",
                context={"error": str(e)},
                cause=e
            )

    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save spray event to database.
        
        Args:
            event: Spray event to save
            
        Raises:
            HTTPException: If save fails
        """
        if not self._pool:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Database not initialized"
            )

        try:
            # Validate field values
            if not all(isinstance(val, (int, float)) and -1e308 <= val <= 1e308 for val in [
                event.x_pos, event.y_pos, event.z_pos,
                event.pressure, event.temperature, event.flow_rate
            ]):
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Field values out of range",
                    context={
                        "fields": {
                            "x_pos": event.x_pos,
                            "y_pos": event.y_pos,
                            "z_pos": event.z_pos,
                            "pressure": event.pressure,
                            "temperature": event.temperature,
                            "flow_rate": event.flow_rate
                        }
                    }
                )

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
                    raise create_error(
                        status_code=status.HTTP_409_CONFLICT,
                        message="Duplicate spray event",
                        context={
                            "sequence_id": event.sequence_id,
                            "spray_index": event.spray_index
                        }
                    )
        except Exception as e:
            if isinstance(e, asyncpg.exceptions.UniqueViolationError):
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Duplicate spray event",
                    context={
                        "sequence_id": event.sequence_id,
                        "spray_index": event.spray_index
                    }
                )
            logger.error(f"Failed to save spray event: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to save spray event",
                context={"error": str(e)},
                cause=e
            )

    async def update_spray_event(self, event_id: int, event: SprayEvent) -> None:
        """Update a spray event in the database.
        
        Args:
            event_id: ID of event to update
            event: Updated spray event data
            
        Raises:
            HTTPException: If update fails
        """
        if not self._pool:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Database not initialized"
            )

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
                    raise create_error(
                        status_code=status.HTTP_404_NOT_FOUND,
                        message="Spray event not found",
                        context={"event_id": event_id}
                    )

                logger.debug(f"Updated spray event {event_id} in database")
        except Exception as e:
            logger.error(f"Failed to update spray event: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to update spray event",
                context={"error": str(e)},
                cause=e
            )

    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence.
        
        Args:
            sequence_id: ID of sequence to get events for
            
        Returns:
            List of spray events
            
        Raises:
            HTTPException: If retrieval fails
        """
        if not self._pool:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Database not initialized"
            )

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
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get spray events",
                context={"error": str(e)},
                cause=e
            )
            
    async def check_connection(self) -> bool:
        """Check database connection.
        
        Returns:
            True if connection is healthy
        """
        if not self._pool:
            return False
            
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return False
            
    async def check_storage(self) -> bool:
        """Check storage functionality.
        
        Returns:
            True if storage is working properly
        """
        if not self._pool:
            return False
            
        try:
            async with self._pool.acquire() as conn:
                # Check if tables exist
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)
                table_names = {t['tablename'] for t in tables}
                required_tables = {'spray_runs', 'spray_events'}
                
                if not required_tables.issubset(table_names):
                    logger.error("Missing required tables")
                    return False
                    
                # Check if indexes exist
                indexes = await conn.fetch("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public'
                """)
                index_names = {i['indexname'] for i in indexes}
                required_indexes = {
                    'idx_spray_runs_sequence_id',
                    'idx_spray_events_run_id'
                }
                
                if not required_indexes.issubset(index_names):
                    logger.error("Missing required indexes")
                    return False
                    
                return True
        except Exception as e:
            logger.error(f"Storage check failed: {str(e)}")
            return False
            
    async def check_health(self) -> Dict[str, Any]:
        """Check storage health.
        
        Returns:
            Health status information
            
        Raises:
            HTTPException: If health check fails
        """
        try:
            health = {
                "status": "ok",
                "connection": await self.check_connection(),
                "storage": await self.check_storage()
            }
            
            if not health["connection"]:
                health["status"] = "error"
                health["error"] = "Database connection failed"
            elif not health["storage"]:
                health["status"] = "error"
                health["error"] = "Storage functionality check failed"
                
            return health
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Storage health check failed",
                context={"error": str(e)},
                cause=e
            )
