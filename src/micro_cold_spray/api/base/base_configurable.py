"""Base configurable service module."""

from typing import TypeVar, Generic, Optional, Dict, Any
from pydantic import BaseModel, ValidationError
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_service import BaseService


T = TypeVar("T", bound=BaseModel)


class ConfigurableService(Generic[T]):
    """Base class for services that require configuration."""

    def __init__(self, config_type: type[T]):
        """Initialize configurable service.
        
        Args:
            config_type: Configuration model type
        """
        self._config: Optional[T] = None
        self._config_type = config_type

    async def configure(self, config: T | Dict[str, Any]) -> None:
        """Configure the service.
        
        Args:
            config: Configuration data or dictionary
            
        Raises:
            HTTPException: If configuration is invalid (422) or service is in invalid state (409)
        """
        if not isinstance(self, BaseService):
            raise create_error(
                message="ConfigurableService must be used with BaseService",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"service": self.__class__.__name__}
            )

        if self.is_running:
            raise create_error(
                message="Cannot configure while service is running",
                status_code=status.HTTP_409_CONFLICT,
                context={"service": self.name}
            )

        try:
            if isinstance(config, dict):
                self._config = self._config_type(**config)
            elif isinstance(config, BaseModel):
                self._config = config
            else:
                raise create_error(
                    message="Invalid configuration type",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    context={
                        "service": self.name,
                        "expected": self._config_type.__name__,
                        "received": type(config).__name__
                    }
                )
        except ValidationError as e:
            raise create_error(
                message="Configuration validation failed",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                context={
                    "service": self.name,
                    "errors": e.errors()
                },
                cause=e
            )

    @property
    def config(self) -> T:
        """Get current configuration.
        
        Returns:
            Current configuration
            
        Raises:
            HTTPException: If service is not configured (409)
        """
        if not self._config:
            raise create_error(
                message="Service is not configured",
                status_code=status.HTTP_409_CONFLICT,
                context={"service": self.name}
            )
        return self._config

    @property
    def is_configured(self) -> bool:
        """Check if service is configured."""
        return self._config is not None
