"""Base configurable class for services that need configuration."""

from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from .base_service import BaseService
from .base_errors import ConfigError, ValidationError


class ConfigurableService(BaseService):
    """Base class for services that require configuration."""

    def __init__(self, service_name: str, config_model: Type[BaseModel]):
        """Initialize configurable service.
        
        Args:
            service_name: Name of the service
            config_model: Pydantic model class for configuration validation
        """
        super().__init__(service_name)
        self._config_model = config_model
        self._config: Optional[BaseModel] = None
        self._is_configured = False

    @property
    def is_configured(self) -> bool:
        """Check if service is configured."""
        return self._is_configured

    @property
    def config(self) -> Optional[BaseModel]:
        """Get current configuration."""
        return self._config

    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure the service with the provided configuration.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ConfigError: If configuration is invalid
            ValidationError: If configuration fails validation
        """
        try:
            # Validate configuration using Pydantic model
            validated_config = self._config_model(**config)
            
            # Additional service-specific validation
            await self._validate_config(validated_config)
            
            self._config = validated_config
            self._is_configured = True
            
        except ValidationError as e:
            raise ConfigError(
                f"Invalid configuration: {str(e)}",
                {"validation_errors": e.context}
            )
        except Exception as e:
            raise ConfigError(f"Failed to configure service: {str(e)}")

    async def _validate_config(self, config: BaseModel) -> None:
        """Validate configuration.
        
        Args:
            config: Validated configuration model
            
        Raises:
            ValidationError: If configuration is invalid
        """
        # Override this method to add custom validation logic
        pass

    async def start(self) -> None:
        """Start the service.
        
        Raises:
            ConfigError: If service is not configured
            ServiceError: If service fails to start
        """
        if not self.is_configured:
            raise ConfigError("Service must be configured before starting")
        await super().start()

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Health check response including configuration status
        """
        health = await super().check_health()
        health["service_info"]["configured"] = self.is_configured
        if self._config:
            health["service_info"]["config"] = self._config.model_dump()
        return health
