"""Database storage implementation for spray events."""

from typing import List, Protocol, Dict, Any
import json
import asyncpg
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


class DataStorage(Protocol):
    """Protocol for data storage implementations."""
    
    async def initialize(self) -> None:
        """Initialize storage (create tables etc)."""
        ...
    
    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save a spray event."""
        ...
    
    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence."""
        ...
        
    async def check_health(self) -> Dict[str, Any]:
        """Check storage health."""
        ...


class DataCollectionStorage:
    """PostgreSQL storage implementation."""
    
    def __init__(self, dsn: str = None):
        """Initialize with database connection string."""
        self._dsn = dsn or "postgresql://postgres:dbpassword@localhost:5432/postgres"
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
                        material_type TEXT NOT NULL,
                        pattern_name TEXT NOT NULL,
                        operator TEXT NOT NULL,
                        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        end_time TIMESTAMP WITH TIME ZONE,
                        powder_size TEXT NOT NULL,
                        powder_lot TEXT NOT NULL,
                        manufacturer TEXT NOT NULL,
                        nozzle_type TEXT NOT NULL,
                        UNIQUE(sequence_id)
                    );

                    CREATE TABLE IF NOT EXISTS spray_events (
                        id SERIAL PRIMARY KEY,
                        run_id INTEGER REFERENCES spray_runs(id),
                        spray_index INTEGER NOT NULL,
                        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        end_time TIMESTAMP WITH TIME ZONE,
                        chamber_pressure_start FLOAT NOT NULL CHECK (chamber_pressure_start >= 0),
                        chamber_pressure_end FLOAT NOT NULL CHECK (chamber_pressure_end >= 0),
                        nozzle_pressure_start FLOAT NOT NULL CHECK (nozzle_pressure_start >= 0),
                        nozzle_pressure_end FLOAT NOT NULL CHECK (nozzle_pressure_end >= 0),
                        main_flow FLOAT NOT NULL CHECK (main_flow >= 0),
                        feeder_flow FLOAT NOT NULL CHECK (feeder_flow >= 0),
                        feeder_frequency FLOAT NOT NULL CHECK (feeder_frequency >= 0),
                        pattern_type TEXT NOT NULL,
                        completed BOOLEAN NOT NULL,
                        error TEXT,
                        UNIQUE(run_id, spray_index)
                    );

                    -- Indexes for faster lookups
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
            logger.error(f"Failed to initialize database: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize database"
            )

    async def save_spray_event(self, event: SprayEvent) -> None:
        """Save spray event to database."""
        if not self._pool:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Database not initialized"
            )

        try:
            async with self._pool.acquire() as conn:
                # Get or create run record
                run_id = await conn.fetchval("""
                    SELECT id FROM spray_runs
                    WHERE sequence_id = $1
                """, event.sequence_id)

                if not run_id:
                    run_params = (
                        event.sequence_id, event.material_type, event.pattern_name,
                        event.operator, event.start_time, event.end_time,
                        event.powder_size, event.powder_lot, event.manufacturer,
                        event.nozzle_type
                    )
                    run_id = await conn.fetchval("""
                        INSERT INTO spray_runs (
                            sequence_id, material_type, pattern_name, operator,
                            start_time, end_time, powder_size, powder_lot,
                            manufacturer, nozzle_type
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        RETURNING id
                    """, *run_params)

                try:
                    event_params = (
                        run_id, event.spray_index, event.start_time, event.end_time,
                        event.chamber_pressure_start, event.chamber_pressure_end,
                        event.nozzle_pressure_start, event.nozzle_pressure_end,
                        event.main_flow, event.feeder_flow, event.feeder_frequency,
                        event.pattern_type, event.completed, event.error
                    )
                    await conn.execute("""
                        INSERT INTO spray_events (
                            run_id, spray_index, start_time, end_time,
                            chamber_pressure_start, chamber_pressure_end,
                            nozzle_pressure_start, nozzle_pressure_end,
                            main_flow, feeder_flow, feeder_frequency,
                            pattern_type, completed, error
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """, *event_params)
                    logger.debug(f"Saved spray event {event.spray_index} to database")
                except asyncpg.exceptions.UniqueViolationError:
                    logger.error(f"Duplicate spray event: {event.spray_index}")
                    raise create_error(
                        status_code=status.HTTP_409_CONFLICT,
                        message="Duplicate spray event"
                    )
        except Exception as e:
            if isinstance(e, asyncpg.exceptions.UniqueViolationError):
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Duplicate spray event"
                )
            logger.error(f"Failed to save spray event: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to save spray event"
            )

    async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence."""
        if not self._pool:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Database not initialized"
            )

        try:
            async with self._pool.acquire() as conn:
                # Get run info first
                run = await conn.fetchrow("""
                    SELECT * FROM spray_runs
                    WHERE sequence_id = $1
                """, sequence_id)
                
                if not run:
                    return []

                # Get all events for this run
                rows = await conn.fetch("""
                    SELECT * FROM spray_events
                    WHERE run_id = $1
                    ORDER BY spray_index
                """, run['id'])
                
                events = []
                for row in rows:
                    events.append(SprayEvent(
                        spray_index=row['spray_index'],
                        sequence_id=sequence_id,
                        material_type=run['material_type'],
                        pattern_name=run['pattern_name'],
                        operator=run['operator'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        powder_size=run['powder_size'],
                        powder_lot=run['powder_lot'],
                        manufacturer=run['manufacturer'],
                        nozzle_type=run['nozzle_type'],
                        chamber_pressure_start=row['chamber_pressure_start'],
                        chamber_pressure_end=row['chamber_pressure_end'],
                        nozzle_pressure_start=row['nozzle_pressure_start'],
                        nozzle_pressure_end=row['nozzle_pressure_end'],
                        main_flow=row['main_flow'],
                        feeder_flow=row['feeder_flow'],
                        feeder_frequency=row['feeder_frequency'],
                        pattern_type=row['pattern_type'],
                        completed=row['completed'],
                        error=row['error']
                    ))
                
                logger.debug(f"Retrieved {len(events)} events for sequence {sequence_id}")
                return events
                
        except Exception as e:
            logger.error(f"Failed to get spray events: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get spray events"
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check storage health."""
        try:
            if not self._pool:
                return {
                    "status": "error",
                    "error": "Database not initialized"
                }
                
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
                return {
                    "status": "ok",
                    "message": "Database connection and schema verified"
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
