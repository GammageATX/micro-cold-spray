"""Configuration file service."""

import yaml
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from ...base import BaseService
from ..models import ConfigData, ConfigMetadata
from ..exceptions import ConfigurationError


class ConfigFileService(BaseService):
    """Service for managing configuration files."""

    def __init__(self, config_dir: Path):
        """Initialize file service.
        
        Args:
            config_dir: Directory for config files
        """
        super().__init__(service_name="config_file")
        self._config_dir = config_dir
        self._config_dir.mkdir(exist_ok=True)

    async def _start(self) -> None:
        """Start file service."""
        try:
            # Ensure config directory exists
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
            # Load and parse config
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                
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

    async def save_config(
        self,
        config_type: str,
        data: Dict[str, Any],
        backup: bool = True
    ) -> None:
        """Save configuration to file.
        
        Args:
            config_type: Type of config to save
            data: Configuration data to save
            backup: Whether to create backup of existing file
            
        Raises:
            ConfigurationError: If config cannot be saved
        """
        config_path = self._config_dir / f"{config_type}.yaml"
        
        try:
            # Create backup if requested
            if backup and config_path.exists():
                backup_path = config_path.with_suffix(".yaml.bak")
                config_path.rename(backup_path)
            
            # Write new config
            with open(config_path, 'w') as f:
                yaml.safe_dump(data, f)
                
            # Remove backup if successful
            if backup:
                backup_path = config_path.with_suffix(".yaml.bak")
                if backup_path.exists():
                    backup_path.unlink()
                    
            logger.info(f"Saved config: {config_type}")
            
        except Exception as e:
            # Restore backup if it exists
            if backup and config_path.with_suffix(".yaml.bak").exists():
                backup_path = config_path.with_suffix(".yaml.bak")
                backup_path.rename(config_path)
                
            raise ConfigurationError(
                f"Failed to save config: {str(e)}",
                {
                    "config_type": config_type,
                    "path": str(config_path),
                    "error": str(e)
                }
            )

    def get_config_timestamp(self, config_type: str) -> float:
        """Get config file modification timestamp.
        
        Args:
            config_type: Type of config to check
            
        Returns:
            File modification timestamp
            
        Raises:
            ConfigurationError: If config file not found
        """
        config_path = self._config_dir / f"{config_type}.yaml"
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Config file not found: {config_type}",
                {"config_type": config_type, "path": str(config_path)}
            )
            
        return config_path.stat().st_mtime

    def config_exists(self, config_type: str) -> bool:
        """Check if config file exists.
        
        Args:
            config_type: Type of config to check
            
        Returns:
            True if config file exists
        """
        config_path = self._config_dir / f"{config_type}.yaml"
        return config_path.exists()
