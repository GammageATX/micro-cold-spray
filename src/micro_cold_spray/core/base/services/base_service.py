"""Base service implementation."""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger


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
    
    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running
    
    @property
    def is_initialized(self) -> bool:
        """Get service initialization state."""
        return self._is_initialized
    
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
        """Start service operation."""
        if self._is_running:
            logger.warning(f"{self._service_name} already running")
            return
        
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
            raise
    
    async def stop(self):
        """Stop service operation."""
        if not self._is_running:
            logger.warning(f"{self._service_name} not running")
            return
        
        try:
            await self._stop()
            self._is_running = False
            self._start_time = None
            logger.info(f"{self._service_name} stopped")
        except Exception as e:
            self._error = str(e)
            logger.error(f"Failed to stop {self._service_name}: {e}")
            raise
    
    async def restart(self):
        """Restart service operation."""
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
                    "ready": self.is_running and not self._error,
                    "version": getattr(self, "version", "1.0.0"),
                    "uptime": self.uptime
                }
            }
            
            # Merge with service-specific info
            health_info.update(base_info)
            
            # Ensure status field exists
            if "status" not in health_info:
                health_info["status"] = "ok" if health_info["service_info"]["ready"] else "not_ready"
            
            return health_info
            
        except Exception as e:
            logger.error(f"Health check failed for {self._service_name}: {e}")
            return {
                "status": "error",
                "service_info": {
                    "ready": False,
                    "version": getattr(self, "version", "1.0.0"),
                    "uptime": self.uptime
                },
                "error": str(e)
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
