# src/micro_cold_spray/core/config/managers/config_manager.py
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
        """
        Initialize config manager.
        
        Args:
            message_broker: MessageBroker for publishing config updates
        """
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

    async def _load_config(self, config_type: str) -> None:
        """
        Load a specific configuration file.
        
        Args:
            config_type: Type of configuration to load
        """
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            logger.debug(f"Attempting to load config from: {config_file.absolute()}")
            
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_file.absolute()}")
                self._configs[config_type] = {}
                return

            with open(config_file, 'r') as f:
                self._configs[config_type] = yaml.safe_load(f) or {}

            logger.info(f"Loaded configuration: {config_type} from {config_file.absolute()}")

        except Exception as e:
            logger.error(f"Error loading config {config_type} from {config_file.absolute()}: {e}")
            raise ConfigurationError(f"Failed to load {config_type} configuration") from e

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """
        Handle configuration update requests from MessageBroker.
        
        Args:
            data: Update request data containing config_type and new_data
        """
        try:
            config_type = data.get("config_type")
            new_data = data.get("new_data")
            
            if not config_type or new_data is None:
                raise ValueError("Invalid config update request")
                
            await self.update_config(config_type, new_data)
            
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._message_broker.publish("config/update/error", {
                "config_type": config_type,
                "error": str(e)
            })

    async def update_config(self, config_type: str, new_data: Dict[str, Any]) -> None:
        """
        Update configuration and notify subscribers.
        
        Args:
            config_type: Type of configuration to update
            new_data: New configuration data
        """
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
        """
        Save configuration to file.
        
        Args:
            config_type: Type of configuration to save
        """
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            with open(config_file, 'w') as f:
                yaml.safe_dump(self._configs[config_type], f)
                
            logger.debug(f"Saved configuration: {config_type}")
            
        except Exception as e:
            logger.error(f"Error saving config {config_type}: {e}")
            raise ConfigurationError(f"Failed to save {config_type} configuration") from e

    def get_config(self, config_type: str) -> Dict[str, Any]:
        """
        Get configuration data.
        
        Args:
            config_type: Type of configuration to retrieve
            
        Returns:
            Configuration data dictionary
        """
        try:
            if config_type not in self._configs:
                logger.warning(f"Config not found: {config_type}")
                return {}
                    
            return self._configs[config_type]
            
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            raise ConfigurationError(f"Failed to get configuration: {str(e)}") from e

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