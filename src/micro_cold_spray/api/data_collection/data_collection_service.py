"""Data collection service."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import HTTPException, status

from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


class DataCollectionService:
    """Service for collecting spray data."""

    def __init__(self, storage: Optional[DataCollectionStorage] = None):
        """Initialize service."""
        self.storage = storage
        self.collecting = False
        self.current_sequence = None

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if not self.storage:
                self.storage = DataCollectionStorage()
                await self.storage.initialize()
            logging.info("Data collection service initialized")
        except Exception as e:
            logging.error(f"Failed to initialize data collection service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to initialize data collection service"
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            self.collecting = False
            self.current_sequence = None
            logging.info("Data collection service stopped")
        except Exception as e:
            logging.error(f"Failed to stop data collection service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to stop data collection service"
            )

    async def start_collection(self, sequence_id: str) -> None:
        """Start data collection for a sequence."""
        try:
            self.collecting = True
            self.current_sequence = sequence_id
            logging.info(f"Started data collection for sequence {sequence_id}")
        except Exception as e:
            logging.error(f"Failed to start data collection: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start data collection"
            )

    async def stop_collection(self) -> None:
        """Stop current data collection."""
        try:
            self.collecting = False
            self.current_sequence = None
            logging.info("Stopped data collection")
        except Exception as e:
            logging.error(f"Failed to stop data collection: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop data collection"
            )

    async def record_spray_event(self, event: SprayEvent) -> None:
        """Record a spray event."""
        try:
            if not self.collecting:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not currently collecting data"
                )
            if event.sequence_id != self.current_sequence:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Event sequence ID does not match current collection sequence"
                )
            await self.storage.save_spray_event(event)
            logging.info(f"Recorded spray event for sequence {event.sequence_id}")
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to record spray event: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record spray event"
            )

    async def get_sequence_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all events for a sequence."""
        try:
            events = await self.storage.get_spray_events(sequence_id)
            logging.info(f"Retrieved {len(events)} events for sequence {sequence_id}")
            return events
        except Exception as e:
            logging.error(f"Failed to get sequence events: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get sequence events"
            )

    async def check_health(self) -> dict:
        """Check service health."""
        try:
            if not self.storage:
                return {
                    "status": "initializing",
                    "collecting": self.collecting,
                    "current_sequence": self.current_sequence,
                    "storage": None
                }
            
            storage_health = await self.storage.check_health() if self.storage else None
            return {
                "status": "ok",
                "collecting": self.collecting,
                "current_sequence": self.current_sequence,
                "storage": storage_health
            }
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Health check failed: {str(e)}"
            )
