"""Data collection service implementation."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from ..base import BaseService
from ..config import ConfigService
from .storage import DataStorage
from .models import SprayEvent, CollectionSession
from .exceptions import DataCollectionError, StorageError


class DataCollectionService(BaseService):
    """Service for managing data collection operations."""

    def __init__(
        self,
        storage: DataStorage,
        config_service: Optional[ConfigService] = None
    ):
        """Initialize data collection service.
        
        Args:
            storage: Storage backend implementation
            config_service: Optional configuration service
        """
        super().__init__("data_collection", config_service)
        self._storage = storage
        self._active_session: Optional[CollectionSession] = None

    async def _start(self) -> None:
        """Initialize service and storage."""
        try:
            # Initialize storage backend
            await self._storage.initialize()
            logger.info("Data collection service started")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {str(e)}")
            raise StorageError("Failed to initialize storage", {"error": str(e)})

    async def _stop(self) -> None:
        """Cleanup service."""
        try:
            # Stop any active collection
            if self._active_session:
                await self.stop_collection()
            logger.info("Data collection service stopped")
        except Exception as e:
            logger.error(f"Error stopping service: {str(e)}")
            raise DataCollectionError("Failed to stop service", {"error": str(e)})

    @property
    def active_session(self) -> Optional[CollectionSession]:
        """Get current active collection session."""
        return self._active_session

    async def start_collection(
        self,
        sequence_id: str,
        collection_params: Dict[str, Any]
    ) -> CollectionSession:
        """Start data collection for a sequence.
        
        Args:
            sequence_id: ID of sequence to collect data for
            collection_params: Collection parameters
            
        Returns:
            Created collection session
            
        Raises:
            DataCollectionError: If collection already in progress or start fails
        """
        if not self.is_running:
            raise DataCollectionError("Service not running")

        if self._active_session:
            raise DataCollectionError(
                "Collection already in progress",
                {"active_sequence": self._active_session.sequence_id}
            )

        try:
            # Create new session
            self._active_session = CollectionSession(
                sequence_id=sequence_id,
                start_time=datetime.now(),
                collection_params=collection_params
            )
            logger.info(f"Started collection for sequence {sequence_id}")
            return self._active_session
            
        except Exception as e:
            logger.error(f"Failed to start collection: {str(e)}")
            raise DataCollectionError(
                "Failed to start collection",
                {"error": str(e)}
            )

    async def stop_collection(self) -> None:
        """Stop current data collection.
        
        Raises:
            DataCollectionError: If no active collection or stop fails
        """
        if not self.is_running:
            raise DataCollectionError("Service not running")

        if not self._active_session:
            raise DataCollectionError("No active collection to stop")

        try:
            # Clear active session
            self._active_session = None
            logger.info("Stopped data collection")
        except Exception as e:
            logger.error(f"Failed to stop collection: {str(e)}")
            raise DataCollectionError(
                "Failed to stop collection",
                {"error": str(e)}
            )

    async def record_spray_event(self, event: SprayEvent) -> None:
        """Record a spray event.
        
        Args:
            event: Spray event to record
            
        Raises:
            DataCollectionError: If no active session or recording fails
        """
        if not self.is_running:
            raise DataCollectionError("Service not running")

        if not self._active_session:
            raise DataCollectionError("No active collection session")

        if event.sequence_id != self._active_session.sequence_id:
            raise DataCollectionError(
                "Event sequence ID does not match active session",
                {
                    "event_sequence": event.sequence_id,
                    "active_sequence": self._active_session.sequence_id
                }
            )

        try:
            await self._storage.save_spray_event(event)
            logger.debug(f"Recorded spray event {event.spray_index}")
        except StorageError as e:
            logger.error(f"Storage error recording event: {str(e)}")
            raise DataCollectionError(
                "Failed to record spray event",
                {"error": str(e), "context": e.context}
            )
        except Exception as e:
            logger.error(f"Failed to record spray event: {str(e)}")
            raise DataCollectionError(
                "Failed to record spray event",
                {"error": str(e)}
            )

    async def get_sequence_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence.
        
        Args:
            sequence_id: ID of sequence to get events for
            
        Returns:
            List of spray events
            
        Raises:
            DataCollectionError: If retrieval fails
        """
        if not self.is_running:
            raise DataCollectionError("Service not running")

        try:
            return await self._storage.get_spray_events(sequence_id)
        except StorageError as e:
            logger.error(f"Storage error getting events: {str(e)}")
            raise DataCollectionError(
                "Failed to get sequence events",
                {"error": str(e), "context": e.context}
            )
        except Exception as e:
            logger.error(f"Failed to get sequence events: {str(e)}")
            raise DataCollectionError(
                "Failed to get sequence events",
                {"error": str(e)}
            )

    async def check_storage(self) -> bool:
        """Check if storage backend is accessible.
        
        Returns:
            True if storage is accessible
        """
        if not self.is_running:
            return False

        try:
            # Try to read/write test data
            test_event = SprayEvent(
                sequence_id="test",
                spray_index=0,
                timestamp=datetime.now(),
                x_pos=0.0,
                y_pos=0.0,
                z_pos=0.0,
                pressure=0.0,
                temperature=0.0,
                flow_rate=0.0,
                status="test"
            )
            await self._storage.save_spray_event(test_event)
            return True
        except Exception as e:
            logger.error(f"Storage check failed: {str(e)}")
            return False
