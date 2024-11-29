# src/micro_cold_spray/core/infrastructure/config/config_manager.py
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from datetime import datetime
import asyncio
from loguru import logger

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.exceptions import ConfigurationError

class ConfigManager:
    """
    Manages application configuration.
    Responsible for loading, storing, and publishing configuration updates.
    """
    
    def __init__(self, message_broker: MessageBroker):
        """Initialize config manager."""
        self._configs: Dict[str, Any] = {}
        self._message_broker = message_broker
        
        # Update config path to look in project root config directory
        self._config_path = Path(__file__).parent.parent.parent.parent.parent.parent / "config"
        self._is_initialized = False
        
        logger.info(f"ConfigManager initialized with config path: {self._config_path.absolute()}")
        logger.debug(f"Config path exists: {self._config_path.exists()}")
        logger.debug(f"Config path contents: {list(self._config_path.glob('*.yaml'))}")

    async def initialize(self) -> None:
        """Initialize configuration system."""
        try:
            if self._is_initialized:
                logger.warning("ConfigManager already initialized")
                return

            # Ensure config directory exists
            self._config_path.mkdir(parents=True, exist_ok=True)

            # Load all config files
            await self._load_all_configs()

            # Subscribe to config update requests
            await self._message_broker.subscribe("config/update/request", self._handle_config_update)

            self._is_initialized = True
            logger.info("ConfigManager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize ConfigManager")
            raise ConfigurationError("Configuration initialization failed") from e

    async def _load_all_configs(self) -> None:
        """Load all configuration files from config directory."""
        try:
            for config_file in self._config_path.glob("*.yaml"):
                config_type = config_file.stem
                await self._load_config(config_type)
                
        except Exception as e:
            logger.exception("Failed to load configurations")
            raise ConfigurationError("Failed to load configuration files") from e

    async def _load_config(self, name: str) -> None:
        """Load configuration from file."""
        try:
            config_file = self._config_path / f"{name}.yaml"
            if not config_file.exists():
                raise ConfigurationError(f"Config file not found: {config_file}")
                
            with open(config_file) as f:
                self._configs[name] = yaml.safe_load(f)
                
            logger.info(f"Loaded configuration: {name} from {config_file}")
            
        except Exception as e:
            logger.error(f"Error loading config {name}: {e}")
            raise ConfigurationError(f"Failed to load config {name}: {str(e)}") from e

    async def get_config(self, name: str) -> Dict[str, Any]:
        """Get configuration by name."""
        try:
            if name not in self._configs:
                await self._load_config(name)
            return self._configs[name]
        except Exception as e:
            logger.error(f"Error getting config {name}: {e}")
            raise ConfigurationError(f"Failed to get config {name}: {str(e)}") from e

    async def update_config(self, config_type: str, new_data: Dict[str, Any]) -> None:
        """Update configuration and notify subscribers."""
        try:
            # Update internal config
            if config_type not in self._configs:
                self._configs[config_type] = {}
            self._configs[config_type].update(new_data)
            
            # Save to file
            await self._save_config(config_type)
            
            # Publish update
            await self._message_broker.publish(
                f"config/update/{config_type}",
                {
                    "config_type": config_type,
                    "data": new_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Configuration updated: {config_type}")
                
        except Exception as e:
            logger.exception(f"Failed to update configuration: {config_type}")
            raise ConfigurationError(f"Configuration update failed: {str(e)}") from e

    async def _save_config(self, config_type: str) -> None:
        """Save configuration to file."""
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            with open(config_file, 'w') as f:
                yaml.safe_dump(self._configs[config_type], f)
                
            logger.debug(f"Saved configuration: {config_type}")
            
        except Exception as e:
            logger.error(f"Error saving config {config_type}: {e}")
            raise ConfigurationError(f"Failed to save {config_type} configuration") from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the config manager."""
        try:
            # Save all configurations
            for config_type in self._configs:
                await self._save_config(config_type)
                
            self._is_initialized = False
            logger.info("ConfigManager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during ConfigManager shutdown")
            raise ConfigurationError(f"Shutdown failed: {str(e)}") from e