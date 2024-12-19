"""Base service implementation."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Type
from loguru import logger
from pydantic import BaseModel
from micro_cold_spray.core.errors.exceptions import ServiceError


class BaseService:
    """Base service class with lifecycle management."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        """Initialize service.
        
        Args:
            service_name: Name of the service
            version: Service version (default: "1.0.0")
        """
        self._service_name = service_name
        self._start_time: Optional[datetime] = None
        self._is_running = False
        self._is_initialized = False
        self._error: Optional[str] = None
        self._message: Optional[str] = None
        self._version = version
        self._settings_model: Optional[Type[BaseModel]] = None
    
    def set_settings_model(self, model: Type[BaseModel]) -> None:
        """Set the Pydantic model for validating settings.
        
        Args:
            model: Pydantic model class for settings validation
        """
        self._settings_model = model
        logger.debug(f"Set settings model for {self._service_name}")
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate settings using the configured Pydantic model.
        
        Args:
            settings: Settings to validate
            
        Returns:
            Validated settings as a dictionary
            
        Raises:
            ValueError: If no settings model is configured
            ValidationError: If settings validation fails
        """
        if not self._settings_model:
            raise ValueError(f"No settings model configured for {self._service_name}")
            
        # Validate settings using Pydantic model
        validated = self._settings_model(**settings)
        return validated.model_dump()
    
    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running
    
    @property
    def is_initialized(self) -> bool:
        """Get service initialization state."""
        return self._is_initialized
    
    @property
    def start_time(self) -> Optional[datetime]:
        """Get service start time."""
        return self._start_time
    
    @property
    def uptime(self) -> Optional[timedelta]:
        """Get service uptime."""
        if self._start_time and self._is_running:
            return datetime.now() - self._start_time
        return None

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def error(self) -> Optional[str]:
        """Get current error message."""
        return self._error

    @property
    def message(self) -> Optional[str]:
        """Get current status message."""
        return self._message

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        """Set service version."""
        self._version = value
    
    async def start(self):
        """Start service operation.
        
        Raises:
            ServiceError: If service fails to start or is already running
        """
        if self._is_running:
            raise ServiceError("Service is already running")
        
        try:
            await self._start()
            self._is_running = True
            self._start_time = datetime.now()
            self._is_initialized = True
            self._error = None
            self._message = None
            logger.info(f"{self._service_name} started")
        except Exception as e:
            self._error = str(e)
            logger.error(f"Failed to start {self._service_name}: {e}")
            raise ServiceError(f"Failed to start service: {str(e)}")
    
    async def stop(self):
        """Stop service operation.
        
        Raises:
            ServiceError: If service fails to stop or is not running
        """
        if not self._is_running:
            raise ServiceError("Service is not running")
        
        try:
            await self._stop()
            self._is_running = False
            self._start_time = None
            logger.info(f"{self._service_name} stopped")
        except Exception as e:
            self._error = str(e)
            logger.error(f"Failed to stop {self._service_name}: {e}")
            raise ServiceError(f"Failed to stop service: {str(e)}")
    
    async def restart(self):
        """Restart service operation.
        
        Raises:
            ServiceError: If service fails to restart or is not running
        """
        if not self._is_running:
            raise ServiceError("Service is not running")
        await self.stop()
        await self.start()
    
    async def check_health(self) -> Dict[str, Any]:
        """Check service health status.
        
        Returns:
            Dict containing health status information
        """
        try:
            # Get service-specific health info
            health_info = await self._check_health()
            
            # Ensure required fields are present
            if not isinstance(health_info, dict):
                health_info = {"status": "error", "error": "Invalid health check response"}
            
            # Add base service info
            base_info = {
                "service_info": {
                    "name": self._service_name,
                    "version": self._version,
                    "running": self._is_running,
                    "ready": self._is_running and not self._error,
                    "uptime": self.uptime.total_seconds() if self.uptime else None
                }
            }
            
            # Add error and message if present
            if self._error:
                base_info["service_info"]["error"] = self._error
            if self._message:
                base_info["service_info"]["message"] = self._message
            
            # Merge with service-specific info
            health_info.update(base_info)
            
            # Set status based on conditions
            if not self._is_running:
                health_info["status"] = "stopped"
            elif self._error:
                health_info["status"] = "error"
                health_info["error"] = self._error
            elif self._message:
                health_info["status"] = "degraded"
                health_info["message"] = self._message
            elif "status" not in health_info:
                health_info["status"] = "ok"
            
            return health_info
            
        except Exception as e:
            logger.error(f"Health check failed for {self._service_name}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "service_info": {
                    "name": self._service_name,
                    "version": self._version,
                    "running": self._is_running,
                    "ready": False,
                    "uptime": self.uptime.total_seconds() if self.uptime else None,
                    "error": str(e)
                }
            }
    
    async def _start(self):
        """Service-specific startup logic."""
        pass
    
    async def _stop(self):
        """Service-specific shutdown logic."""
        pass
    
    async def _check_health(self) -> Dict[str, Any]:
        """Service-specific health check logic."""
        if not self._is_initialized:
            raise RuntimeError("Service not initialized")
        return {}
