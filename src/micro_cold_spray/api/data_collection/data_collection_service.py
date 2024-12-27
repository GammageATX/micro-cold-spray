"""Data collection service."""

import os
import yaml
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


def load_config() -> Dict[str, Any]:
    """Load data collection configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config_path = os.path.join("config", "data_collection.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class DataCollectionService:
    """Service for collecting spray data."""

    def __init__(self, storage: Optional[DataCollectionStorage] = None):
        """Initialize service."""
        self._service_name = "data_collection"
        self._version = "1.0.0"  # Will be updated from config
        self._is_running = False
        self._start_time = None
        self._config = None
        self._mode = "normal"  # Default to normal mode
        
        # Initialize components to None
        self._storage = storage
        self._collecting = False
        self._current_sequence = None
        
        logger.info(f"{self._service_name} service initialized")

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            # Load config first
            self._config = load_config()
            self._version = self._config["service"]["version"]
            self._mode = self._config.get("service", {}).get("mode", self._mode)  # Get mode from config
            
            # Initialize storage if not provided
            if not self._storage:
                db_config = self._config["database"]
                dsn = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                self._storage = DataCollectionStorage(dsn=dsn, pool_config=db_config["pool"])
                await self._storage.initialize()
                
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            if not self._storage:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )

            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started")

        except Exception as e:
            self._is_running = False
            self._start_time = None
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )

            self._is_running = False
            self._start_time = None
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Get health from components
            storage_health = await self._storage.health() if self._storage else None
            
            # Build component statuses
            components = {
                "storage": ComponentHealth(
                    status="ok" if storage_health and storage_health.status == "ok" else "error",
                    error=storage_health.error if storage_health else "Component not initialized"
                ),
                "collector": ComponentHealth(
                    status="ok" if self.is_running else "error",
                    error=None if self.is_running else "Collector not running"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                mode=self._mode,
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                mode=self._mode,
                components={name: ComponentHealth(status="error", error=error_msg)
                            for name in ["storage", "collector"]}
            )

    async def start_collection(self, sequence_id: str) -> None:
        """Start data collection for a sequence."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"{self.service_name} service not running"
                )
                
            self._collecting = True
            self._current_sequence = sequence_id
            logger.info(f"Started data collection for sequence {sequence_id}")
            
        except Exception as e:
            error_msg = f"Failed to start data collection: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop_collection(self) -> None:
        """Stop current data collection."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"{self.service_name} service not running"
                )
                
            self._collecting = False
            self._current_sequence = None
            logger.info("Stopped data collection")
            
        except Exception as e:
            error_msg = f"Failed to stop data collection: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
