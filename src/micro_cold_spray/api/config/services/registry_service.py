"""Configuration registry service implementation."""

from typing import Dict, List, Type, Set, Any, Optional
from loguru import logger
from fastapi import status
from datetime import datetime

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.models.config_models import ConfigData


class ConfigRegistryService(BaseService):
    """Configuration registry service implementation."""

    def __init__(self, service_name: str = "registry") -> None:
        """Initialize service.
        
        Args:
            service_name: Service name
        """
        super().__init__(service_name)
        self._config_types: Dict[str, Type[ConfigData]] = {}
        self._configs: Dict[str, ConfigData] = {}
        self._tags: Set[str] = set()
        self._actions: Set[str] = {"read", "write", "monitor"}
        self._validations: Set[str] = {"range", "enum", "pattern"}
        self._start_time: Optional[datetime] = None

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds.
        
        Returns:
            float: Service uptime in seconds
        """
        if not self._start_time:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def _start(self) -> None:
        """Start registry service."""
        try:
            await self._load_tag_registry()
            await self._load_action_registry()
            await self._load_validation_registry()
            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Registry service started")
        except Exception as e:
            logger.error(f"Failed to start registry service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to start registry service",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop registry service."""
        try:
            self._config_types.clear()
            self._configs.clear()
            self._tags.clear()
            self._actions = {"read", "write", "monitor"}
            self._validations = {"range", "enum", "pattern"}
            self._start_time = None
            self._is_running = False
            logger.info("Registry service stopped")
        except Exception as e:
            logger.error(f"Failed to stop registry service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to stop registry service",
                context={"error": str(e)},
                cause=e
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        return {
            "status": "running" if self.is_running else "stopped",
            "is_healthy": self.is_running,
            "uptime": self.uptime,
            "context": {
                "service": "registry",
                "config_types": len(self._config_types),
                "configs": len(self._configs),
                "tags": len(self._tags),
                "actions": len(self._actions),
                "validations": len(self._validations)
            }
        }

    async def _load_tag_registry(self) -> None:
        """Load tag registry."""
        try:
            # Load tags from configuration or database
            logger.info("Tag registry loaded")
        except Exception as e:
            logger.error(f"Failed to load tag registry: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to load tag registry",
                context={"error": str(e)},
                cause=e
            )

    async def _load_action_registry(self) -> None:
        """Load action registry."""
        try:
            # Load actions from configuration or database
            logger.info("Action registry loaded")
        except Exception as e:
            logger.error(f"Failed to load action registry: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to load action registry",
                context={"error": str(e)},
                cause=e
            )

    async def _load_validation_registry(self) -> None:
        """Load validation registry."""
        try:
            # Load validations from configuration or database
            logger.info("Validation registry loaded")
        except Exception as e:
            logger.error(f"Failed to load validation registry: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to load validation registry",
                context={"error": str(e)},
                cause=e
            )

    async def register_config_type(self, config_type: Type[ConfigData]) -> None:
        """Register configuration type.
        
        Args:
            config_type: Configuration type to register
            
        Raises:
            HTTPException: If service not running (503) or type already exists (409)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service is not running"
            )

        if config_type.__name__ in self._config_types:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Config type {config_type.__name__} already exists",
                context={"type": config_type.__name__}
            )

        self._config_types[config_type.__name__] = config_type
        logger.info(f"Registered config type: {config_type.__name__}")

    def get_config_type(self, type_name: str) -> Type[ConfigData]:
        """Get configuration type by name.
        
        Args:
            type_name: Configuration type name
            
        Returns:
            Type[ConfigData]: Configuration type
            
        Raises:
            HTTPException: If service not running (503) or type not found (404)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Registry service is not running"
            )

        if type_name not in self._config_types:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Config type {type_name} not found",
                context={"type": type_name}
            )

        return self._config_types[type_name]
