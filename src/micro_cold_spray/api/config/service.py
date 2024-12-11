"""Configuration service implementation."""

import yaml
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from .main import CONFIG_DIR


class ConfigurationError(Exception):
    """Raised when configuration operations fail."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message)
        self.context = context or {}


class ConfigService:
    """Service for managing configuration files."""

    def __init__(self):
        """Initialize config service."""
        self._config_cache: Dict[str, Dict] = {}
        self._last_modified: Dict[str, float] = {}
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start config service."""
        self._is_running = True
        logger.info("Config service started")

    async def stop(self) -> None:
        """Stop config service."""
        self._is_running = False
        self._config_cache.clear()
        self._last_modified.clear()
        logger.info("Config service stopped")

    async def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get configuration by type.
        
        Args:
            config_type: Type of config to get (e.g. "hardware", "tags")
            
        Returns:
            Dict containing configuration data
            
        Raises:
            ConfigurationError: If config cannot be loaded
        """
        if not self.is_running:
            raise ConfigurationError(
                "Config service not running",
                {"config_type": config_type}
            )
            
        config_path = CONFIG_DIR / f"{config_type}.yaml"
        
        # Check if file exists
        if not config_path.exists():
            raise ConfigurationError(
                f"Config file not found: {config_type}",
                {"config_type": config_type, "path": str(config_path)}
            )
            
        # Get last modified time
        last_modified = config_path.stat().st_mtime
        
        # Return cached config if not modified
        if (config_type in self._config_cache and config_type in self.last_modified and self._last_modified[config_type] >= last_modified):
            return self._config_cache[config_type]
            
        try:
            # Load and parse config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Update cache
            self._config_cache[config_type] = config
            self._last_modified[config_type] = last_modified
            
            logger.debug(f"Loaded config: {config_type}")
            return config
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load config: {str(e)}",
                {
                    "config_type": config_type,
                    "path": str(config_path),
                    "error": str(e)
                }
            )

    async def update_config(
        self,
        config_type: str,
        config: Dict[str, Any]
    ) -> None:
        """Update configuration by type.
        
        Args:
            config_type: Type of config to update
            config: New configuration data
            
        Raises:
            ConfigurationError: If config cannot be updated
        """
        if not self.is_running:
            raise ConfigurationError(
                "Config service not running",
                {"config_type": config_type}
            )
            
        config_path = CONFIG_DIR / f"{config_type}.yaml"
        
        try:
            # Create backup
            if config_path.exists():
                backup_path = config_path.with_suffix(".yaml.bak")
                config_path.rename(backup_path)
            
            # Write new config
            with open(config_path, 'w') as f:
                yaml.safe_dump(config, f)
                
            # Update cache
            self._config_cache[config_type] = config
            self._last_modified[config_type] = datetime.now().timestamp()
            
            # Remove backup
            backup_path = config_path.with_suffix(".yaml.bak")
            if backup_path.exists():
                backup_path.unlink()
                
            logger.info(f"Updated config: {config_type}")
            
        except Exception as e:
            # Restore backup if it exists
            if config_path.with_suffix(".yaml.bak").exists():
                backup_path = config_path.with_suffix(".yaml.bak")
                backup_path.rename(config_path)
                
            raise ConfigurationError(
                f"Failed to update config: {str(e)}",
                {
                    "config_type": config_type,
                    "path": str(config_path),
                    "error": str(e)
                }
            )

    async def check_status(self) -> bool:
        """Check if config service is healthy."""
        try:
            return self.is_running
        except Exception as e:
            logger.error(f"Config status check failed: {str(e)}")
            return False
