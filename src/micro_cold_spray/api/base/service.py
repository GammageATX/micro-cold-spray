"""Base service functionality."""

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
        """Check service health status."""
        try:
            # Get service-specific health info
            health_info = await self._check_health()
            
            # Add base service info
            health_info.update({
                "service_info": {
                    "name": self._service_name,
                    "version": self.version,
                    "running": self._is_running,
                    "uptime": str(self.uptime) if self.uptime else None
                }
            })
            
            # Set status based on service state
            if not self._is_initialized:
                health_info["status"] = "error"
                health_info["error"] = "Service not initialized"
                health_info["service_info"]["error"] = "Service not initialized"
            elif not self._is_running:
                health_info["status"] = "stopped"
                if self._error:
                    health_info["error"] = self._error
                    health_info["service_info"]["error"] = self._error
            elif self._error:
                health_info["status"] = "error"
                health_info["error"] = self._error
                health_info["service_info"]["error"] = self._error
            elif self._message:
                health_info["status"] = "degraded"
                health_info["message"] = self._message
                health_info["service_info"]["message"] = self._message
            else:
                health_info["status"] = "ok"
            
            return health_info
        except Exception as e:
            self._error = str(e)
            return {
                "status": "error",
                "error": str(e),
                "service_info": {
                    "name": self._service_name,
                    "version": self.version,
                    "running": self._is_running,
                    "uptime": str(self.uptime) if self.uptime else None,
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
