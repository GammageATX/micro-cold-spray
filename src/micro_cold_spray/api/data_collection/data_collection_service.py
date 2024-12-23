"""Data collection service."""

import os
import yaml
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import HTTPException, status

from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent
from micro_cold_spray.utils.errors import create_error


class DataCollectionService:
    """Service for collecting spray data."""

    def __init__(self, storage: Optional[DataCollectionStorage] = None):
        """Initialize service."""
        self.storage = storage
        self.collecting = False
        self.current_sequence = None
        self._config = {}
        self._name = "data_collection"
        self._version = "1.0.0"
        self._is_running = False
        self._start_time = None

    async def _load_config(self) -> Dict[str, Any]:
        """Load service configuration.
        
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

    @property
    def name(self) -> str:
        """Get service name."""
        return self._name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            # Load config first
            self._config = await self._load_config()
            self._version = self._config["service"]["version"]
            
            # Initialize storage if not provided
            if not self.storage:
                db_config = self._config["database"]
                dsn = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                self.storage = DataCollectionStorage(dsn=dsn, pool_config=db_config["pool"])
                await self.storage.initialize()
                
            self._is_running = True
            self._start_time = datetime.now()
            logging.info("Data collection service initialized")
            
        except Exception as e:
            logging.error(f"Failed to initialize data collection service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to initialize data collection service: {str(e)}"
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            self.collecting = False
            self.current_sequence = None
            self._is_running = False
            logging.info("Data collection service stopped")
        except Exception as e:
            logging.error(f"Failed to stop data collection service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop data collection service: {str(e)}"
            )

    async def start_collection(self, sequence_id: str) -> None:
        """Start data collection for a sequence."""
        try:
            if not self._is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            self.collecting = True
            self.current_sequence = sequence_id
            logging.info(f"Started data collection for sequence {sequence_id}")
            
        except Exception as e:
            logging.error(f"Failed to start data collection: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to start data collection: {str(e)}"
            )

    async def stop_collection(self) -> None:
        """Stop current data collection."""
        try:
            if not self._is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            self.collecting = False
            self.current_sequence = None
            logging.info("Stopped data collection")
            
        except Exception as e:
            logging.error(f"Failed to stop data collection: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to stop data collection: {str(e)}"
            )

    async def record_spray_event(self, event: SprayEvent) -> None:
        """Record a spray event."""
        try:
            if not self._is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if not self.collecting:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Not currently collecting data"
                )
                
            if event.sequence_id != self.current_sequence:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Event sequence ID does not match current collection sequence"
                )
                
            await self.storage.save_spray_event(event)
            logging.info(f"Recorded spray event for sequence {event.sequence_id}")
            
        except Exception as e:
            logging.error(f"Failed to record spray event: {e}")
            if isinstance(e, HTTPException):
                raise
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to record spray event: {str(e)}"
            )

    async def get_sequence_events(self, sequence_id: str) -> List[SprayEvent]:
        """Get all events for a sequence."""
        try:
            if not self._is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            events = await self.storage.get_spray_events(sequence_id)
            logging.info(f"Retrieved {len(events)} events for sequence {sequence_id}")
            return events
            
        except Exception as e:
            logging.error(f"Failed to get sequence events: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get sequence events: {str(e)}"
            )

    async def check_health(self) -> dict:
        """Check service health."""
        try:
            if not self._is_running:
                return {
                    "status": "error",
                    "message": "Service not running",
                    "collecting": False,
                    "current_sequence": None,
                    "storage": None,
                    "uptime": 0
                }
            
            storage_health = await self.storage.check_health() if self.storage else None
            uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            
            return {
                "status": "ok",
                "version": self._version,
                "collecting": self.collecting,
                "current_sequence": self.current_sequence,
                "storage": storage_health,
                "uptime": uptime
            }
            
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Health check failed: {str(e)}"
            )
