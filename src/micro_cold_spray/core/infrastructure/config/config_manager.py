# src/micro_cold_spray/core/infrastructure/config/config_manager.py
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union, Optional
import yaml
from loguru import logger

from micro_cold_spray.core.exceptions import ConfigurationError
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker


class ConfigManager:
    """
    Manages application configuration.
    Responsible for loading, storing, and publishing configuration updates.
    """

    # Required configuration files
    REQUIRED_CONFIGS = [
        'application',
        'file_format',
        'hardware',
        'process',
        'state',
        'tags'
    ]

    def __init__(self, config_path: Union[str, Path], message_broker: Optional[MessageBroker] = None) -> None:
        """Initialize with config path."""
        self._config_path = Path(config_path)
        self._message_broker = message_broker
        self._configs: Dict[str, Any] = {}
        self._is_initialized = False

        logger.info(f"ConfigManager initialized with config path: {self._config_path}")
        logger.debug(f"Config path exists: {self._config_path.exists()}")
        logger.debug(f"Config path contents: {list(self._config_path.glob('*.yaml'))}")

    async def initialize(self) -> None:
        """Initialize configuration manager."""
        try:
            # Load all config files
            for config_file in self._config_path.glob("*.yaml"):
                config_type = config_file.stem
                await self._load_config(config_type)

            # Subscribe to config messages if message broker is available
            if self._message_broker:
                await self._message_broker.subscribe("config/request", self._handle_config_request)

            self._is_initialized = True
            logger.info("Configuration manager initialized")

        except Exception as e:
            error_msg = f"Failed to initialize ConfigManager: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    async def _load_config(self, config_type: str) -> None:
        """Load a configuration file."""
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            if not config_file.exists():
                raise ConfigurationError(f"Config not found: {config_type}")

            with open(config_file, 'r', encoding='utf-8', newline='') as f:
                config_data = yaml.safe_load(f)
                if config_data is None:
                    raise ConfigurationError(f"Empty config file: {config_type}")

            self._configs[config_type] = config_data
            logger.debug(f"Loaded config: {config_type}")

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in config {config_type}: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
        except Exception as e:
            error_msg = str(e) if isinstance(e, ConfigurationError) else f"Failed to load config {config_type}: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    async def _handle_config_request(self, data: Dict[str, Any]) -> None:
        """Handle config request messages."""
        request_id = data.get("request_id", "")
        try:
            request_type = data.get("request_type")
            config_type = data.get("config") or data.get("config_type")

            if not request_type:
                await self._send_error("Missing request_type", request_id)
                return

            if not config_type:
                await self._send_error("Missing config type", request_id)
                return

            response_data = {
                "request_id": request_id,
                "config": config_type,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }

            if request_type == "get" or request_type == "load":
                if config_type not in self._configs:
                    await self._load_config(config_type)
                response_data["data"] = self._configs[config_type]

            elif request_type == "save":
                config_data = data.get("data")
                if not config_data:
                    await self._send_error("Missing config data", request_id)
                    return

                # Save config
                self._configs[config_type] = config_data
                config_file = self._config_path / f"{config_type}.yaml"
                with open(config_file, 'w', encoding='utf-8', newline='') as f:
                    yaml.dump(config_data, f)

                response_data["status"] = "saved"

                # Notify subscribers
                await self._message_broker.publish(
                    "config/update",
                    {
                        "config": config_type,
                        "data": config_data,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            elif request_type == "update":
                update_data = data.get("data")
                if not update_data:
                    await self._send_error("Missing config data", request_id)
                    return

                # Validate and update
                await self._validate_config(config_type, update_data)
                await self.update_config(config_type, update_data)

                response_data["status"] = "updated"

            else:
                await self._send_error(f"Invalid request_type: {request_type}", request_id)
                return

            # Send single success response
            await self._message_broker.publish("config/response", response_data)

        except Exception as e:
            error_msg = f"Failed to handle config request: {str(e)}"
            await self._send_error(error_msg, request_id)

    async def _send_error(self, error_msg: str, request_id: str) -> None:
        """Send error response."""
        error_context = {
            "source": "config_manager",
            "error": error_msg,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }

        # Send to error topic
        await self._message_broker.publish("error", error_context)

        # Send error response
        await self._message_broker.publish(
            "config/response",
            {
                "success": False,
                "error": error_msg,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
        )

    async def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get configuration by type."""
        try:
            if config_type not in self._configs:
                await self._load_config(config_type)
            return self._configs[config_type]

        except Exception as e:
            error_msg = str(e) if isinstance(e, ConfigurationError) else f"Config not found: {config_type}"
            error_context = {
                "source": "config_manager",
                "error": error_msg,
                "config_type": config_type,
                "operation": "get",
                "timestamp": datetime.now().isoformat()
            }
            await self._message_broker.publish("error", error_context)
            raise ConfigurationError(error_msg) from e

    async def update_config(self, config_type: str, update_data: Dict[str, Any]) -> None:
        """Update configuration."""
        try:
            # Create config file if it doesn't exist
            config_file = self._config_path / f"{config_type}.yaml"
            if not config_file.exists():
                with open(config_file, 'w', encoding='utf-8', newline='') as f:
                    yaml.dump({}, f)

            # Load config if not already loaded
            if config_type not in self._configs:
                await self._load_config(config_type)

            # Initialize empty config if needed
            if not self._configs.get(config_type):
                self._configs[config_type] = {}

            # Validate update data
            await self._validate_config(config_type, update_data)

            # Merge updates with existing config
            self._configs[config_type] = self._deep_merge(self._configs[config_type], update_data)

            # Save updated config
            with open(config_file, 'w', encoding='utf-8', newline='') as f:
                yaml.dump(self._configs[config_type], f)

            logger.debug(f"Updated config file: {config_file}")

            # Notify subscribers of update
            await self._message_broker.publish(
                "config/update",
                {
                    "config_type": config_type,
                    "config": self._configs[config_type],
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = str(e) if isinstance(e, ConfigurationError) else f"Failed to update config: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        merged = base.copy()
        for key, value in update.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    async def shutdown(self) -> None:
        """Shutdown the config manager."""
        try:
            self._is_initialized = False
            logger.info("Configuration manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during ConfigManager shutdown: {e}")
            raise ConfigurationError("Failed to shutdown ConfigManager") from e

    # Add validation methods
    async def _validate_config(self, config_type: str, config_data: Dict[str, Any]) -> None:
        """Basic config validation."""
        try:
            # Get current config for structure comparison
            current = self._configs.get(config_type, {})

            # For application config, ensure critical sections exist
            if config_type == "application":
                required_sections = ["application"]  # Version is optional
                missing = [s for s in required_sections if s not in config_data]
                if missing:
                    raise ConfigurationError(f"Missing required sections: {missing}")

                # Check application subsections
                if "application" in config_data:
                    required_app_sections = ["info", "paths", "environment", "services"]
                    app_data = config_data["application"]
                    missing = [s for s in required_app_sections if s not in app_data]
                    if missing:
                        raise ConfigurationError(f"Missing required application sections: {missing}")

            # For other configs, ensure root structure matches
            else:
                current_keys = set(current.keys())
                new_keys = set(config_data.keys())
                if not new_keys.issubset(current_keys):
                    invalid = new_keys - current_keys
                    raise ConfigurationError(f"Invalid config sections: {invalid}")

        except Exception as e:
            error_msg = str(e) if isinstance(e, ConfigurationError) else f"Invalid config data: {str(e)}"
            raise ConfigurationError(error_msg)
