"""File service for config operations."""

from pathlib import Path
from datetime import datetime
import yaml
from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata


class ConfigFileService(BaseService):
    """Service for file operations."""

    def __init__(self, config_dir: Path):
        """Initialize file service."""
        super().__init__(service_name="config_file")
        self._config_dir = config_dir
        self._config_dir.mkdir(exist_ok=True)

    async def _start(self) -> None:
        """Start file service."""
        try:
            self._config_dir.mkdir(exist_ok=True)
            logger.info("Config file service started")
        except Exception as e:
            raise ConfigurationError("Failed to start file service", {"error": str(e)})

    async def load_config(self, config_type: str) -> ConfigData:
        """Load configuration from file.
        
        Args:
            config_type: Type of config to load
            
        Returns:
            Loaded configuration data
            
        Raises:
            ConfigurationError: If config cannot be loaded
        """
        config_path = self._config_dir / f"{config_type}.yaml"
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Config file not found: {config_type}",
                {"config_type": config_type, "path": str(config_path)}
            )
            
        try:
            logger.debug(f"Loading config from {config_path}")
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                logger.debug(f"Loaded YAML data: {data.keys()}")
                
            # Handle nested config structure
            if config_type in data:
                data = data[config_type]
                
            metadata = ConfigMetadata(
                config_type=config_type,
                last_modified=datetime.fromtimestamp(config_path.stat().st_mtime)
            )
            
            return ConfigData(metadata=metadata, data=data)
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load config: {str(e)}",
                {
                    "config_type": config_type,
                    "path": str(config_path),
                    "error": str(e)
                }
            )

    async def save_config(self, config_data: ConfigData) -> None:
        """Save configuration to file."""
        config_type = config_data.metadata.config_type
        config_path = self._config_dir / f"{config_type}.yaml"
        
        try:
            # Create backup
            if config_path.exists():
                backup_path = config_path.with_suffix(".yaml.bak")
                config_path.rename(backup_path)
            
            # Atomic write using temporary file
            temp_path = config_path.with_suffix(".yaml.tmp")
            with open(temp_path, 'w') as f:
                yaml.safe_dump(config_data.data, f)
            temp_path.rename(config_path)
            
        except Exception as e:
            logger.error(f"Failed to save config {config_type}: {e}")
            raise ConfigurationError(
                f"Failed to save config: {e}",
                {
                    "config_type": config_type,
                    "path": str(config_path)
                }
            )

    def config_exists(self, config_type: str) -> bool:
        """Check if config file exists."""
        config_path = self._config_dir / f"{config_type}.yaml"
        return config_path.exists()
