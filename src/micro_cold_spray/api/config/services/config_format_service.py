"""Configuration format service implementation."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Type

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models.config_models import ConfigData


class ConfigFormat:
    """Base configuration format."""

    def __init__(self, extension: str) -> None:
        """Initialize format.

        Args:
            extension: File extension
        """
        self.extension = extension

    def load(self, path: Path) -> Dict[str, Any]:
        """Load configuration from file.

        Args:
            path: File path

        Returns:
            Configuration data

        Raises:
            ConfigError: If load fails
        """
        raise NotImplementedError

    def save(self, path: Path, data: Dict[str, Any]) -> None:
        """Save configuration to file.

        Args:
            path: File path
            data: Configuration data

        Raises:
            ConfigError: If save fails
        """
        raise NotImplementedError


class JsonFormat(ConfigFormat):
    """JSON configuration format."""

    def __init__(self) -> None:
        """Initialize format."""
        super().__init__(".json")

    def load(self, path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file.

        Args:
            path: File path

        Returns:
            Configuration data

        Raises:
            ConfigError: If load fails
        """
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ConfigError("Failed to load JSON", {"error": str(e)})

    def save(self, path: Path, data: Dict[str, Any]) -> None:
        """Save configuration to JSON file.

        Args:
            path: File path
            data: Configuration data

        Raises:
            ConfigError: If save fails
        """
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise ConfigError("Failed to save JSON", {"error": str(e)})


class YamlFormat(ConfigFormat):
    """YAML configuration format."""

    def __init__(self) -> None:
        """Initialize format."""
        super().__init__(".yaml")

    def load(self, path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Args:
            path: File path

        Returns:
            Configuration data

        Raises:
            ConfigError: If load fails
        """
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ConfigError("Failed to load YAML", {"error": str(e)})

    def save(self, path: Path, data: Dict[str, Any]) -> None:
        """Save configuration to YAML file.

        Args:
            path: File path
            data: Configuration data

        Raises:
            ConfigError: If save fails
        """
        try:
            with open(path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            raise ConfigError("Failed to save YAML", {"error": str(e)})


class ConfigFormatService(BaseService):
    """Configuration format service implementation."""

    def __init__(self, service_name: str) -> None:
        """Initialize service.

        Args:
            service_name: Service name
        """
        super().__init__(service_name)
        self._formats: Dict[str, ConfigFormat] = {}

    async def _start(self) -> None:
        """Start format service."""
        try:
            # Register default formats
            self.register_format(JsonFormat())
            self.register_format(YamlFormat())
            logger.info("Format service started with {} formats", len(self._formats))
        except Exception as e:
            raise ConfigError("Failed to start format service", {"error": str(e)})

    def register_format(self, format_handler: ConfigFormat) -> None:
        """Register configuration format.

        Args:
            format_handler: Format handler to register

        Raises:
            ConfigError: If format already exists
        """
        if format_handler.extension in self._formats:
            raise ConfigError(f"Format {format_handler.extension} already registered")

        self._formats[format_handler.extension] = format_handler
        logger.info("Registered format: {}", format_handler.extension)

    def get_format(self, extension: str) -> Optional[ConfigFormat]:
        """Get format handler by extension.

        Args:
            extension: File extension

        Returns:
            Format handler if found
        """
        return self._formats.get(extension)

    def get_format_for_path(self, path: Path) -> ConfigFormat:
        """Get format handler for file path.

        Args:
            path: File path

        Returns:
            Format handler

        Raises:
            ConfigError: If format not found
        """
        extension = path.suffix
        format_handler = self.get_format(extension)
        if not format_handler:
            raise ConfigError(f"Unsupported format: {extension}")
        return format_handler

    async def load_config(self, path: Path) -> ConfigData:
        """Load configuration from file.

        Args:
            path: File path

        Returns:
            Configuration data

        Raises:
            ConfigError: If load fails
        """
        format_handler = self.get_format_for_path(path)
        try:
            data = format_handler.load(path)
            return ConfigData(**data)
        except Exception as e:
            raise ConfigError("Failed to load config", {"error": str(e)})

    async def save_config(self, path: Path, config: ConfigData) -> None:
        """Save configuration to file.

        Args:
            path: File path
            config: Configuration data

        Raises:
            ConfigError: If save fails
        """
        format_handler = self.get_format_for_path(path)
        try:
            format_handler.save(path, config.model_dump())
        except Exception as e:
            raise ConfigError("Failed to save config", {"error": str(e)})

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "formats": list(self._formats.keys())
        })
        return health
