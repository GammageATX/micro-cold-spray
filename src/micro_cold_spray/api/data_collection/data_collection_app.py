"""Data collection API application."""

import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, status

from micro_cold_spray.api.data_collection.data_collection_router import router
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage


class DataCollectionApp(FastAPI):
    """Data collection application."""

    def __init__(self):
        """Initialize application."""
        super().__init__(
            title="Data Collection API",
            description="API for collecting spray data",
            version="1.0.0"
        )
        
        # Initialize components
        self.service: Optional[DataCollectionService] = None
        self.storage: Optional[DataCollectionStorage] = None
        
        # Add routes
        self.include_router(router)
        
        # Add event handlers
        self.add_event_handler("startup", self.startup_event)
        self.add_event_handler("shutdown", self.shutdown_event)

    async def startup_event(self):
        """Initialize service on startup."""
        try:
            logging.info("Starting data collection service...")
            
            # Get database connection string from environment
            dsn = os.getenv("DATABASE_URL", "postgresql://postgres:dbpassword@localhost:5432/postgres")
            
            # Initialize storage first
            self.storage = DataCollectionStorage(dsn)
            await self.storage.initialize()
            
            # Initialize service with storage
            self.service = DataCollectionService(storage=self.storage)
            await self.service.initialize()
            
            logging.info("Data collection service started")
            
        except Exception as e:
            logging.error(f"Failed to start data collection service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to start data collection service"
            )

    async def shutdown_event(self):
        """Stop service on shutdown."""
        try:
            logging.info("Stopping data collection service...")
            if self.service:
                await self.service.stop()
            logging.info("Data collection service stopped")
        except Exception as e:
            logging.error(f"Failed to stop data collection service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to stop data collection service"
            )
