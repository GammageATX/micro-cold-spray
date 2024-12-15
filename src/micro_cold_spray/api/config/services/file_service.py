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
        self._backup_suffix = ".bak"

    async def _start(self) -> None:
        """Start file service."""
        try:
            self._config_dir.mkdir(exist_ok=True)
            logger.info("Config file service started")
        except Exception as e:
            logger.error(f"Failed to start file service: {e}")
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
        config_path = self._get_config_path(config_type)
        
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
        """Save configuration to file with backup handling."""
        config_type = config_data.metadata.config_type
        config_path = self._get_config_path(config_type)
        
        try:
            # Create config directory if it doesn't exist
            self._config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            if config_path.exists():
                await self.create_backup(config_type)
            
            # Write new config
            with open(config_path, 'w') as f:
                yaml.safe_dump(config_data.data, f)
            
        except Exception as e:
            logger.error(f"Failed to save config {config_type}: {e}")
            raise ConfigurationError(
                f"Failed to save config: {e}",
                {
                    "config_type": config_type,
                    "path": str(config_path)
                }
            )

    async def config_exists(self, config_type: str) -> bool:
        """Check if config file exists.
        
        Args:
            config_type: Type of configuration to check
            
        Returns:
            True if config file exists, False otherwise
        """
        if config_type.endswith(self._backup_suffix):
            # For backup files, strip the suffix and check backup path
            base_type = config_type[:-len(self._backup_suffix)]
            return self._get_backup_path(base_type).exists()
        return self._get_config_path(config_type).exists()

    async def create_backup(self, config_type: str) -> None:
        """Create a backup of the config file.
        
        Args:
            config_type: Type of configuration to backup
            
        Raises:
            ConfigurationError: If backup creation fails
        """
        source_path = self._get_config_path(config_type)
        backup_path = self._get_backup_path(config_type)
        
        if not source_path.exists():
            raise ConfigurationError(
                f"Config file not found: {config_type}",
                {"config_type": config_type, "path": str(source_path)}
            )
            
        try:
            # Copy the file with metadata preserved
            import shutil
            shutil.copy2(source_path, backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup for {config_type}: {e}")
            raise ConfigurationError(
                f"Failed to create backup for {config_type}",
                {"config_type": config_type, "error": str(e)}
            )

    def _get_config_path(self, config_type: str) -> Path:
        """Get the path for a config file."""
        return self._config_dir / f"{config_type}.yaml"

    def _get_backup_path(self, config_type: str) -> Path:
        """Get the path for a config backup file."""
        return self._config_dir / f"{config_type}.yaml{self._backup_suffix}"
