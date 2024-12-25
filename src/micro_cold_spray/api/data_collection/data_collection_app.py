"""Data collection API application."""

import os
import yaml
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from micro_cold_spray.api.data_collection.data_collection_router import router
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage
from micro_cold_spray.utils.errors import create_error


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
        self._config: Dict[str, Any] = {}
        self._start_time: Optional[datetime] = None
        
        # Add CORS middleware
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add routes
        self.include_router(router)
        
        # Add health endpoint
        @self.get("/health")
        async def health():
            """Health check endpoint."""
            try:
                uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
                return {
                    "status": "ok",
                    "service": "data_collection",
                    "version": self.version,
                    "is_running": bool(self.service and self.storage),
                    "uptime": uptime,
                    "error": None,
                    "timestamp": datetime.now()
                }
            except Exception as e:
                return {
                    "status": "error",
                    "service": "data_collection",
                    "version": self.version,
                    "is_running": False,
                    "uptime": 0,
                    "error": str(e),
                    "timestamp": datetime.now()
                }
        
        # Add event handlers
        self.add_event_handler("startup", self.startup_event)
        self.add_event_handler("shutdown", self.shutdown_event)

    async def _load_config(self) -> Dict[str, Any]:
        """Load application configuration.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        try:
            config_path = os.path.join("config", "data_collection.yaml")
            if not os.path.exists(config_path):
                logging.warning(f"Config file not found at {config_path}, using defaults")
                return {
                    "service": {
                        "version": "1.0.0",
                        "host": "0.0.0.0",
                        "port": 8006,
                        "history_retention_days": 30
                    },
                    "database": {
                        "host": "localhost",
                        "port": 5432,
                        "user": "postgres",
                        "password": "dbpassword",
                        "database": "postgres",
                        "pool": {
                            "min_size": 2,
                            "max_size": 10,
                            "command_timeout": 60.0
                        }
                    }
                }

            with open(config_path, 'r') as f:
                return yaml.safe_load(f)

        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to load configuration: {str(e)}"
            )

    async def startup_event(self):
        """Initialize service on startup."""
        try:
            logging.info("Starting data collection service...")
            
            # Set start time
            self._start_time = datetime.now()
            
            # Load configuration
            self._config = await self._load_config()
            
            # Get database configuration
            db_config = self._config["database"]
            dsn = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            
            # Initialize storage first
            self.storage = DataCollectionStorage(dsn=dsn, pool_config=db_config["pool"])
            await self.storage.initialize()
            
            # Initialize service with storage
            self.service = DataCollectionService(storage=self.storage)
            await self.service.initialize()
            
            logging.info("Data collection service started")
            
        except Exception as e:
            logging.error(f"Failed to start data collection service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start data collection service: {str(e)}"
            )

    async def shutdown_event(self):
        """Cleanup on shutdown."""
        try:
            if self.service:
                await self.service.stop()
            logging.info("Data collection service stopped")
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
            # Don't raise here as we're shutting down
