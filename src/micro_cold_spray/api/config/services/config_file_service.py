"""Configuration file service implementation."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models.config_models import ConfigData


class ConfigFileService(BaseService):
    """Configuration file service implementation."""

    def __init__(self, service_name: str, config_dir: Path) -> None:
        """Initialize service.

        Args:
            service_name: Service name
            config_dir: Configuration directory
        """
        super().__init__(service_name)
        self._config_dir = config_dir
        self._backup_dir = config_dir / "backup"

    async def _start(self) -> None:
        """Start file service."""
        try:
            self._config_dir.mkdir(exist_ok=True)
            self._backup_dir.mkdir(exist_ok=True)
            logger.info("File service started")
        except Exception as e:
            raise ConfigError("Failed to start file service", {"error": str(e)})

    def exists(self, config_type: str) -> bool:
        """Check if configuration file exists.

        Args:
            config_type: Configuration type

        Returns:
            True if file exists
        """
        config_file = self._config_dir / f"{config_type}.json"
        return config_file.exists()

    async def load_config(self, config_type: str) -> ConfigData:
        """Load configuration from file.

        Args:
            config_type: Configuration type

        Returns:
            Configuration data

        Raises:
            ConfigError: If load fails
        """
        config_file = self._config_dir / f"{config_type}.json"
        if not config_file.exists():
            raise ConfigError(f"Config file not found: {config_file}")

        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
            return ConfigData(**config_data)
        except Exception as e:
            raise ConfigError("Failed to load config", {"error": str(e)})

    async def save_config(self, config: ConfigData, create_backup: bool = True) -> None:
        """Save configuration to file.

        Args:
            config: Configuration data
            create_backup: Create backup of existing file

        Raises:
            ConfigError: If save fails
        """
        config_file = self._config_dir / f"{config.metadata.config_type}.json"

        try:
            if create_backup and config_file.exists():
                await self.create_backup(config.metadata.config_type)

            with open(config_file, "w") as f:
                json.dump(config.model_dump(), f, indent=2)
        except Exception as e:
            raise ConfigError("Failed to save config", {"error": str(e)})

    async def create_backup(self, config_type: str) -> Optional[Path]:
        """Create backup of configuration file.

        Args:
            config_type: Configuration type

        Returns:
            Backup file path if created

        Raises:
            ConfigError: If backup fails
        """
        config_file = self._config_dir / f"{config_type}.json"
        if not config_file.exists():
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self._backup_dir / f"{config_type}_{timestamp}.json"
            shutil.copy2(config_file, backup_file)
            return backup_file
        except Exception as e:
            raise ConfigError("Failed to create backup", {"error": str(e)})

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "config_dir": str(self._config_dir),
            "backup_dir": str(self._backup_dir),
            "config_files": len(list(self._config_dir.glob("*.json"))),
            "backup_files": len(list(self._backup_dir.glob("*.json")))
        })
        return health
