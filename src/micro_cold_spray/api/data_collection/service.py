"""Data collection service implementation."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from ..base import ConfigurableService
from ..config import ConfigService
from .storage import DataStorage
from .models import SprayEvent, CollectionSession
from .exceptions import DataCollectionError, StorageError


class DataCollectionService(ConfigurableService):
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
        super().__init__("data_collection")
        self._storage = storage
        self._config_service = config_service
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
        """Check storage health."""
        if not self.is_running:
            return False
        
        try:
            # Check basic connectivity
            if not await self._storage.check_connection():
                logger.error("Storage connection check failed")
                return False
            
            # Check storage functionality
            if not await self._storage.check_storage():
                logger.error("Storage functionality check failed")
                return False
            
            # Check health status
            health = await self._storage.check_health()
            if health["status"] != "ok":
                logger.error(f"Storage health check failed: {health.get('error', 'Unknown error')}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Storage check failed: {str(e)}")
            return False

    async def check_health(self) -> dict:
        """Check service health status."""
        health = await super().check_health()
        
        if not self.is_running:
            return health
        
        try:
            # Check storage health
            storage_health = await self._storage.check_health()
            if storage_health["status"] != "ok":
                health["status"] = "error"
                health["error"] = storage_health.get("error")
                return health
            
            # Add storage health info
            health.update(storage_health)
            
            # Add active session info if exists
            if self._active_session:
                health["active_sequence"] = self._active_session.sequence_id
        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
        
        return health
