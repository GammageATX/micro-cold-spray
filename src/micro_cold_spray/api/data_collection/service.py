"""Data collection service implementation."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from .storage import DataStorage

logger = logging.getLogger(__name__)


class DataCollectionError(Exception):
    """Base exception for data collection errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


@dataclass
class SprayEvent:
    """Data class representing a spray event."""
    sequence_id: str
    spray_index: int
    timestamp: datetime
    x_pos: float
    y_pos: float
    z_pos: float
    pressure: float
    temperature: float
    flow_rate: float
    status: str


@dataclass
class CollectionSession:
    """Active data collection session info."""
    sequence_id: str
    start_time: datetime
    collection_params: Dict[str, Any]


class DataCollectionService:
    """Service for managing data collection operations."""

    def __init__(self, storage: DataStorage):
        """Initialize with storage backend."""
        self._storage = storage
        self._active_session: Optional[CollectionSession] = None

    @property
    def active_session(self) -> Optional[CollectionSession]:
        """Get current active collection session."""
        return self._active_session

    async def start_collection(self, sequence_id: str, collection_params: Dict[str, Any]) -> None:
        """Start data collection for a sequence."""
        if self._active_session:
            raise DataCollectionError(
                "Collection already in progress",
                {"active_sequence": self._active_session.sequence_id}
            )

        try:
            self._active_session = CollectionSession(
                sequence_id=sequence_id,
                start_time=datetime.now(),
                collection_params=collection_params
            )
            logger.info(f"Started collection for sequence {sequence_id}")
        except Exception as e:
            raise DataCollectionError(f"Failed to start collection: {str(e)}")

    async def stop_collection(self) -> None:
        """Stop current data collection."""
        if not self._active_session:
            raise DataCollectionError("No active collection to stop")

        try:
            self._active_session = None
            logger.info("Stopped data collection")
        except Exception as e:
            raise DataCollectionError(f"Failed to stop collection: {str(e)}")

    async def record_spray_event(self, event: SprayEvent) -> None:
        """Record a spray event."""
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
        except Exception as e:
            raise DataCollectionError(f"Failed to record spray event: {str(e)}")

    async def get_sequence_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all spray events for a sequence."""
        try:
            return await self._storage.get_spray_events(sequence_id)
        except Exception as e:
            raise DataCollectionError(f"Failed to get sequence events: {str(e)}")

    async def check_storage(self) -> bool:
        """Check if storage backend is accessible."""
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
