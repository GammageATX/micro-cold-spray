"""Base configurable service module."""

from typing import TypeVar, Generic, Type
from fastapi import status, HTTPException
from pydantic import BaseModel, ValidationError

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error


ConfigType = TypeVar("ConfigType", bound=BaseModel)


class ConfigurableService(BaseService, Generic[ConfigType]):
    """Base configurable service."""

    def __init__(self, config_class: Type[ConfigType], name: str = None):
        """Initialize configurable service."""
        super().__init__(name)
        self.config_class = config_class
        self.config = None

    def configure(self, config: ConfigType | dict) -> None:
        """Configure the service.
        
        Args:
            config: Configuration data
            
        Raises:
            HTTPException: If configuration is invalid
        """
        try:
            if isinstance(config, dict):
                config = self.config_class(**config)
            elif not isinstance(config, BaseModel):
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid configuration type",
                    context={
                        "service": self.name,
                        "expected": self.config_class.__name__,
                        "received": type(config).__name__
                    }
                )
            
            # Validate the config even if it's already a BaseModel
            if isinstance(config, BaseModel):
                config = self.config_class.model_validate(config)
                
            self.config = config
        except ValidationError as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Configuration validation failed",
                context={
                    "service": self.name,
                    "errors": e.errors()
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to configure service",
                context={
                    "service": self.name,
                    "error": str(e)
                },
                cause=e
            )

    @property
    def is_configured(self) -> bool:
        """Check if service is configured."""
        return self.config is not None
