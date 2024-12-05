# src/micro_cold_spray/core/infrastructure/config/config_manager.py
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import yaml
from loguru import logger
from micro_cold_spray.core.exceptions import ConfigurationError
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
import os


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

            # Subscribe to config requests
            await self._message_broker.subscribe(
                "config/update/request",  # Config update request topic
                self._handle_config_update  # Handler method
            )
            await self._message_broker.subscribe(
                "config/get",  # Config get request topic
                self._handle_config_get  # Handler method
            )

            self._is_initialized = True
            logger.info("ConfigManager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize ConfigManager")
            raise ConfigurationError("Configuration initialization failed") from e

    async def _load_all_configs(self) -> None:
        """Load all configuration files from config directory."""
        try:
            config_files = [
                "application",
                "file_format",
                "hardware",
                "process",
                "state",
                "tags"
            ]

            for config_type in config_files:
                await self._load_config(config_type)

            logger.info("All configuration files loaded successfully")

        except Exception as e:
            logger.exception("Failed to load configurations")
            raise ConfigurationError("Failed to load configuration files") from e

    async def _load_config(self, config_type: str) -> None:
        """Load configuration from file."""
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            logger.debug(f"Loading config file: {config_file}")

            # Read with explicit encoding
            with open(config_file, 'r', encoding='utf-8', newline='') as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                config_data = {}

            self._configs[config_type] = config_data
            logger.debug(f"Loaded config {config_type}: {config_data}")

        except Exception as e:
            logger.error(f"Error loading config file {config_type}: {str(e)}")
            raise ConfigurationError(f"Failed to load config file {config_type}") from e

    async def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get configuration by type."""
        try:
            if not config_type:
                raise ValueError("No config type specified for config get operation")

            # Add logging to track config requests
            logger.debug(f"Getting config for type: {config_type}")

            if config_type not in self._configs:
                # Load config if not in cache
                await self._load_config(config_type)

            config = self._configs.get(config_type, {})

            # Add debug logging
            if isinstance(config, dict):
                logger.debug(f"Config {config_type} keys: {list(config.keys())}")
                if config_type == "hardware" and "hardware" in config:
                    logger.debug(f"Hardware config structure: {list(config['hardware'].keys())}")

            return config

        except Exception as e:
            logger.error(f"Error getting config for type {config_type}: {str(e)}")
            raise ConfigurationError(f"Failed to get config for {config_type}") from e

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        merged = base.copy()
        for key, value in update.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    async def update_config(self, config_type: str, new_data: Dict[str, Any]) -> None:
        """Update configuration and notify subscribers."""
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            logger.debug(f"Updating config file: {config_file} (absolute: {config_file.absolute()})")

            # Read current file content with explicit encoding
            with open(config_file, 'r', encoding='utf-8', newline='') as f:
                current_data = yaml.safe_load(f)
                if current_data is None:
                    current_data = {}
                logger.debug(f"Read current data: {current_data}")

            # For application config, handle environment updates
            if config_type == "application" and "application" in new_data:
                if "environment" in new_data["application"]:
                    env_update = new_data["application"]["environment"]
                    logger.debug(f"Applying environment updates: {env_update}")

                    # Ensure environment section exists
                    if "application" not in current_data:
                        current_data["application"] = {}
                    if "environment" not in current_data["application"]:
                        current_data["application"]["environment"] = {}

                    # Update fields directly
                    for key, value in env_update.items():
                        if key == "user_history":
                            # Special handling for user_history list
                            current_history = current_data["application"]["environment"].get("user_history", [])
                            # Add any new users that aren't already in the list
                            for user in value:
                                if user not in current_history:
                                    current_history.append(user)
                            current_data["application"]["environment"]["user_history"] = current_history
                        else:
                            current_data["application"]["environment"][key] = value
                        logger.debug(f"Updated {key} to: {value}")
            else:
                # For other configs, do deep merge
                current_data = self._deep_merge(current_data, new_data)
                logger.debug(f"Deep merged data: {current_data}")

            # Update in-memory config
            self._configs[config_type] = current_data
            logger.debug(f"Updated in-memory config for {config_type}")

            # Write to string first to verify YAML
            yaml_str = yaml.dump(current_data, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2)
            logger.debug(f"Generated YAML:\n{yaml_str}")

            # Write to file with explicit encoding
            logger.debug(f"Writing to file: {config_file}")
            with open(config_file, 'w', encoding='utf-8', newline='') as f:
                f.write(yaml_str)
                f.flush()  # Flush buffers to disk
                os.fsync(f.fileno())  # Force write to disk

            # Verify write
            logger.debug("Verifying file was written")
            with open(config_file, 'r', encoding='utf-8', newline='') as f:
                verify_data = yaml.safe_load(f)
                logger.debug(f"Read back data: {verify_data}")

                # Deep compare the data
                if verify_data != current_data:
                    logger.error("Verification failed - data mismatch!")
                    logger.error(f"Expected: {current_data}")
                    logger.error(f"Got: {verify_data}")
                else:
                    logger.debug("Verification passed - data matches")

            # Verify file on disk
            logger.debug(f"Verifying file exists on disk: {config_file.exists()}")
            if config_file.exists():
                logger.debug(f"File size: {config_file.stat().st_size} bytes")
                with open(config_file, 'rb') as f:
                    logger.debug(f"First 100 bytes: {f.read(100)}")

            # Notify subscribers
            await self._message_broker.publish(
                f"config/update/{config_type}",
                {
                    "config_type": config_type,
                    "data": new_data,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "config_update",
                "config_type": config_type,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Failed to update configuration: {error_msg}")
            await self._message_broker.publish("error", error_msg)
            raise ConfigurationError("Configuration update failed", error_msg)

    async def _save_config(self, config_type: str) -> None:
        """Save configuration to file."""
        try:
            config_file = self._config_path / f"{config_type}.yaml"

            # Add version if it's missing
            config_data = self._configs[config_type].copy()
            if config_type == "application" and "version" not in config_data:
                config_data["version"] = "1.0.0"

            logger.debug(f"Saving config to {config_file}: {config_data}")

            # Ensure proper YAML formatting
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2)

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

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle configuration update requests."""
        try:
            config_type = data.get("config_type")
            new_data = data.get("data")

            if not config_type or not new_data:
                error_context = {
                    "received_data": data,
                    "timestamp": datetime.now().isoformat()
                }
                raise ConfigurationError(
                    "Invalid config update request - missing required fields",
                    error_context)

            await self.update_config(config_type, new_data)

        except Exception as e:
            error_context = {
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error handling config update: {error_context}")
            raise ConfigurationError(
                "Failed to handle config update",
                error_context) from e

    async def _handle_config_get(self, data: Dict[str, Any]) -> None:
        """Handle configuration get requests."""
        try:
            config_type = data.get("config_type")
            key = data.get("key")

            if not config_type:
                raise ConfigurationError("No config type specified")

            # Get the config
            config = await self.get_config(config_type)

            # Extract specific key if provided
            if key:
                # Navigate nested keys
                value = config
                for k in key.split('.'):
                    value = value.get(k, {})
            else:
                value = config

            # Send response
            await self._message_broker.publish(
                "config/response",
                {
                    "config_type": config_type,
                    "key": key,
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = {
                "error": str(e),
                "config_type": config_type if 'config_type' in locals() else None,
                "key": key if 'key' in locals() else None,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Failed to get configuration: {error_msg}")
            await self._message_broker.publish(
                "config/error",
                error_msg
            )
