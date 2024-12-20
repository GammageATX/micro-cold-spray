"""Configuration file service implementation."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from loguru import logger
from fastapi import HTTPException, status

from micro_cold_spray.api.base.base_service import BaseService


class ConfigFileService(BaseService):
    """Configuration file service implementation."""

    def __init__(self, config_dir: Path, backup_dir: Path, service_name: str = "file") -> None:
        """Initialize service.

        Args:
            config_dir: Configuration directory
            backup_dir: Backup directory
            service_name: Service name
        """
        super().__init__(service_name)
        self._config_dir = config_dir
        self._backup_dir = backup_dir
        self.backup_enabled = True

    async def _start(self) -> None:
        """Start implementation."""
        # Create directories if they don't exist
        self._config_dir.mkdir(exist_ok=True)
        self._backup_dir.mkdir(exist_ok=True)
        logger.info("File service started")

    async def _stop(self) -> None:
        """Stop implementation."""
        logger.info("File service stopped")

    async def exists(self, config_type: str) -> bool:
        """Check if configuration exists.

        Args:
            config_type: Configuration type

        Returns:
            True if exists
        """
        config_file = self._config_dir / config_type
        return config_file.exists()

    async def create_backup(self, config_file: Path) -> Optional[Path]:
        """Create backup of configuration file.

        Args:
            config_file: Configuration file path

        Returns:
            Backup file path if created
        """
        if not self.backup_enabled or not config_file.exists():
            return None

        # Create backup filename with timestamp including microseconds
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{config_file.stem}_{timestamp}.bak"
        backup_path = self._backup_dir / backup_name

        # Copy file to backup
        with open(config_file, "r") as src, open(backup_path, "w") as dst:
            dst.write(src.read())

        logger.debug("Created backup: {}", backup_path)
        return backup_path

    async def load_config(self, config_type: str) -> Dict[str, Any]:
        """Load configuration from file.

        Args:
            config_type: Configuration type

        Returns:
            Configuration data

        Raises:
            HTTPException: If load fails
        """
        config_file = self._config_dir / config_type
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Config file not found",
                    "file": str(config_file)
                }
            )

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f)
                if data is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Config file is empty",
                            "file": str(config_file)
                        }
                    )
                return data
        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML in {}: {}", config_type, str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid YAML format",
                    "file": str(config_file),
                    "error": str(e)
                }
            )
        except Exception as e:
            logger.error("Failed to load config {}: {}", config_type, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Failed to load config",
                    "file": str(config_file),
                    "error": str(e)
                }
            )

    async def save_config(self, config_type: str, config: Dict[str, Any], create_backup: bool = True) -> None:
        """Save configuration to file.

        Args:
            config_type: Configuration type
            config: Configuration data
            create_backup: Create backup of existing file

        Raises:
            HTTPException: If save fails
        """
        config_file = self._config_dir / config_type

        try:
            # Create backup if enabled
            if create_backup and config_file.exists():
                await self.create_backup(config_file)

            # Save config
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)

            logger.debug("Saved config: {}", config_type)
        except Exception as e:
            logger.error("Failed to save config {}: {}", config_type, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Failed to save config",
                    "file": str(config_file),
                    "error": str(e)
                }
            )

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "config_dir": str(self._config_dir),
            "backup_dir": str(self._backup_dir),
            "backup_enabled": self.backup_enabled
        })
        return health
