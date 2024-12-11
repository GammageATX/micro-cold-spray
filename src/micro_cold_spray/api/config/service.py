"""Configuration service implementation."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml
from loguru import logger

from ..base import BaseService
from ...core.infrastructure.messaging.message_broker import MessageBroker


class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message)
        self.context = context or {}


class ConfigService(BaseService):
    """Service for managing application configuration."""

    REQUIRED_CONFIGS = [
        "application",
        "hardware",
        "process",
        "validation"
    ]

    def __init__(self, message_broker: MessageBroker, config_dir: Path):
        """Initialize with message broker and config directory."""
        super().__init__()
        self._message_broker = message_broker
        self._config_dir = config_dir
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._last_modified: Dict[str, datetime] = {}

    async def start(self) -> None:
        """Initialize the service."""
        await super().start()
        
        # Create config directory if it doesn't exist
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate required configs exist
        for config_type in self.REQUIRED_CONFIGS:
            config_path = self._get_config_path(config_type)
            if not config_path.exists():
                raise ConfigurationError(
                    f"Required config file missing: {config_type}",
                    {"path": str(config_path)}
                )
        
        logger.info(f"Using config directory: {self._config_dir}")

    def _get_config_path(self, config_type: str) -> Path:
        """Get path for config file."""
        return self._config_dir / f"{config_type}.yaml"

    async def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get configuration by type."""
        config_path = self._get_config_path(config_type)
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Config file not found: {config_type}",
                {"path": str(config_path)}
            )
            
        # Check if cached version is still valid
        last_modified = datetime.fromtimestamp(config_path.stat().st_mtime)
        if (config_type in self._config_cache and 
            config_type in self._last_modified and
            self._last_modified[config_type] >= last_modified):
            return self._config_cache[config_type]
            
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Cache the config
            self._config_cache[config_type] = config
            self._last_modified[config_type] = last_modified
            
            return config
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in config file: {config_type}",
                {"error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to read config file: {config_type}",
                {"error": str(e)}
            )

    async def update_config(self, config_type: str, config_data: Dict[str, Any]) -> None:
        """Update configuration."""
        # Validate config first
        await self.validate_config(config_type, config_data)
        
        config_path = self._get_config_path(config_type)
        try:
            # Create backup
            if config_path.exists():
                backup_path = config_path.with_suffix(f".yaml.bak")
                config_path.rename(backup_path)
            
            # Write new config
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, sort_keys=False)
                
            # Update cache
            self._config_cache[config_type] = config_data
            self._last_modified[config_type] = datetime.fromtimestamp(config_path.stat().st_mtime)
            
            # Notify update
            await self._message_broker.publish(
                "config/updated",
                {
                    "type": config_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Updated config: {config_type}")
        except Exception as e:
            # Restore backup if it exists
            if config_path.with_suffix(f".yaml.bak").exists():
                backup_path = config_path.with_suffix(f".yaml.bak")
                backup_path.rename(config_path)
                
            raise ConfigurationError(
                f"Failed to update config: {config_type}",
                {"error": str(e)}
            )

    async def validate_config(self, config_type: str, config_data: Dict[str, Any]) -> None:
        """Validate configuration data."""
        try:
            # Basic YAML validation
            yaml.dump(config_data)
            
            # Type-specific validation
            if config_type == "application":
                self._validate_application_config(config_data)
            elif config_type == "hardware":
                self._validate_hardware_config(config_data)
            elif config_type == "process":
                self._validate_process_config(config_data)
            elif config_type == "validation":
                self._validate_validation_config(config_data)
            else:
                logger.warning(f"No specific validation for config type: {config_type}")
                
        except yaml.YAMLError as e:
            raise ConfigurationError(
                "Invalid YAML format",
                {"error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"Configuration validation failed: {config_type}",
                {"error": str(e)}
            )

    def _validate_application_config(self, config: Dict[str, Any]) -> None:
        """Validate application configuration."""
        required_fields = ["paths", "logging", "ui"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(
                    f"Missing required field in application config: {field}"
                )

    def _validate_hardware_config(self, config: Dict[str, Any]) -> None:
        """Validate hardware configuration."""
        required_fields = ["plc", "motion", "gas"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(
                    f"Missing required field in hardware config: {field}"
                )

    def _validate_process_config(self, config: Dict[str, Any]) -> None:
        """Validate process configuration."""
        required_fields = ["parameters", "limits", "sequences"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(
                    f"Missing required field in process config: {field}"
                )

    def _validate_validation_config(self, config: Dict[str, Any]) -> None:
        """Validate validation configuration."""
        required_fields = ["rules", "thresholds"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(
                    f"Missing required field in validation config: {field}"
                )

    async def check_config_access(self) -> bool:
        """Check if config files are accessible."""
        try:
            for config_type in self.REQUIRED_CONFIGS:
                config_path = self._get_config_path(config_type)
                if not config_path.exists():
                    logger.error(f"Required config file missing: {config_type}")
                    return False
                    
                # Try reading the file
                with open(config_path, 'r') as f:
                    yaml.safe_load(f)
                    
            return True
        except Exception as e:
            logger.error(f"Config access check failed: {str(e)}")
            return False