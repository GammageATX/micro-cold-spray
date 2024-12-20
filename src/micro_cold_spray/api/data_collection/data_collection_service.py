"""Data collection service implementation."""

from typing import Optional, List
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_configurable import ConfigurableService
from .data_collection_models import SprayEvent
from .data_collection_storage import DataStorage


class DataCollectionService(ConfigurableService):
    """Service for collecting and storing spray data."""
    
    def __init__(self, storage: DataStorage):
        """Initialize with storage backend."""
        super().__init__()
        self._storage = storage
        self._is_collecting = False
        self._current_sequence: Optional[str] = None
        self._spray_index = 0
        
    async def initialize(self) -> None:
        """Initialize service and storage.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            await self._storage.initialize()
            logger.info("Data collection service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize data collection: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize data collection service",
                context={"error": str(e)},
                cause=e
            )
            
    async def start_collection(self, sequence_id: str) -> None:
        """Start collecting data for a sequence.
        
        Args:
            sequence_id: ID of sequence to collect data for
            
        Raises:
            HTTPException: If collection cannot be started
        """
        if self._is_collecting:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message="Data collection already in progress",
                context={"current_sequence": self._current_sequence}
            )
            
        try:
            self._current_sequence = sequence_id
            self._spray_index = 0
            self._is_collecting = True
            logger.info(f"Started data collection for sequence {sequence_id}")
        except Exception as e:
            logger.error(f"Failed to start data collection: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to start data collection",
                context={"error": str(e)},
                cause=e
            )
            
    async def stop_collection(self) -> None:
        """Stop current data collection.
        
        Raises:
            HTTPException: If collection cannot be stopped
        """
        if not self._is_collecting:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message="No data collection in progress"
            )
            
        try:
            self._is_collecting = False
            self._current_sequence = None
            self._spray_index = 0
            logger.info("Stopped data collection")
        except Exception as e:
            logger.error(f"Failed to stop data collection: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to stop data collection",
                context={"error": str(e)},
                cause=e
            )
            
    async def record_spray_event(
        self,
        x_pos: float,
        y_pos: float,
        z_pos: float,
        pressure: float,
        temperature: float,
        flow_rate: float,
        status: str = "active"
    ) -> None:
        """Record a spray event.
        
        Args:
            x_pos: X position
            y_pos: Y position
            z_pos: Z position
            pressure: Gas pressure
            temperature: Gas temperature
            flow_rate: Powder flow rate
            status: Event status
            
        Raises:
            HTTPException: If event cannot be recorded
        """
        if not self._is_collecting:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message="No data collection in progress"
            )
            
        try:
            event = SprayEvent(
                sequence_id=self._current_sequence,
                spray_index=self._spray_index,
                timestamp=datetime.now(),
                x_pos=x_pos,
                y_pos=y_pos,
                z_pos=z_pos,
                pressure=pressure,
                temperature=temperature,
                flow_rate=flow_rate,
                status=status
            )
            
            await self._storage.save_spray_event(event)
            self._spray_index += 1
            logger.debug(f"Recorded spray event {self._spray_index}")
        except Exception as e:
            logger.error(f"Failed to record spray event: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to record spray event",
                context={"error": str(e)},
                cause=e
            )
            
    async def get_sequence_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all events for a sequence.
        
        Args:
            sequence_id: ID of sequence to get events for
            
        Returns:
            List of spray events
            
        Raises:
            HTTPException: If events cannot be retrieved
        """
        try:
            events = await self._storage.get_spray_events(sequence_id)
            logger.debug(f"Retrieved {len(events)} events for sequence {sequence_id}")
            return events
        except Exception as e:
            logger.error(f"Failed to get sequence events: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get sequence events",
                context={"error": str(e)},
                cause=e
            )
            
    async def check_health(self) -> dict:
        """Check service health.
        
        Returns:
            Health status information
            
        Raises:
            HTTPException: If health check fails
        """
        try:
            storage_health = await self._storage.check_health()
            
            health = {
                "status": "ok",
                "collecting": self._is_collecting,
                "current_sequence": self._current_sequence,
                "spray_index": self._spray_index,
                "storage": storage_health
            }
            
            if storage_health["status"] != "ok":
                health["status"] = "error"
                health["error"] = storage_health.get("error", "Storage check failed")
                
            return health
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service health check failed",
                context={"error": str(e)},
                cause=e
            )
