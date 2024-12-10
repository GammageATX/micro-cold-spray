from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger

from ..base import BaseService
from ...core.exceptions import ConfigurationError
from ...core.infrastructure.messaging.message_broker import MessageBroker

class ConfigService(BaseService):
    """Service for managing application configuration."""

    REQUIRED_CONFIGS = [
        'application',
        'file_format',
        'hardware',
        'process',
        'state',
        'tags'
    ]

    def __init__(
        self,
        config_path: Path,
        message_broker: MessageBroker
    ):
        super().__init__(service_name="config")
        self._config_path = config_path
        self._message_broker = message_broker
        self._configs: Dict[str, Any] = {}
        
    async def start(self) -> None:
        """Initialize configuration service."""
        await super().start()
        try:
            # Load all config files
            for config_file in self._config_path.glob("*.yaml"):
                config_type = config_file.stem
                await self._load_config(config_type)

            # Subscribe to config messages
            await self._message_broker.subscribe(
                "config/request", 
                self._handle_config_request
            )

            logger.info("Configuration service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize ConfigService: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    async def _load_config(self, config_type: str) -> None:
        """Load a configuration file."""
        try:
            config_file = self._config_path / f"{config_type}.yaml"
            if not config_file.exists():
                raise ConfigurationError(f"Config not found: {config_type}")

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if config_data is None:
                    raise ConfigurationError(f"Empty config file: {config_type}")

            self._configs[config_type] = config_data
            logger.debug(f"Loaded config: {config_type}")

        except Exception as e:
            error_msg = f"Failed to load config {config_type}: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg) 

    async def validate_config(self, config_type: str, config_data: Dict[str, Any]) -> None:
        """Validate configuration data."""
        try:
            # Validate based on config type
            if config_type == "application":
                await self._validate_application_config(config_data)
            elif config_type == "process":
                await self._validate_process_config(config_data)
            elif config_type == "hardware":
                await self._validate_hardware_config(config_data)
            elif config_type == "state":
                await self._validate_state_config(config_data)
            elif config_type == "tags":
                await self._validate_tag_config(config_data)
            else:
                raise ConfigurationError(f"Unknown config type: {config_type}")
                
        except Exception as e:
            error_msg = f"Config validation failed: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    async def _validate_process_config(self, config: Dict[str, Any]) -> None:
        """Validate process config specifics."""
        try:
            if "process" not in config:
                raise ConfigurationError("Missing process root section")
                
            process = config["process"]
            
            # Validate action groups
            if "action_groups" in process:
                for group_name, group_def in process["action_groups"].items():
                    if "steps" not in group_def:
                        raise ConfigurationError(f"Action group missing steps: {group_name}")
                        
            # Validate atomic actions
            if "atomic_actions" in process:
                for action_name, action_def in process["atomic_actions"].items():
                    if "messages" not in action_def:
                        raise ConfigurationError(f"Atomic action missing messages: {action_name}")
                        
            # Validate validation rules
            if "validation" in process:
                if not isinstance(process["validation"], dict):
                    raise ConfigurationError("Invalid validation rules format")
                    
        except Exception as e:
            raise ConfigurationError(f"Process config validation failed: {str(e)}")

    async def _validate_hardware_config(self, config: Dict[str, Any]) -> None:
        """Validate hardware config specifics."""
        try:
            if "hardware" not in config:
                raise ConfigurationError("Missing hardware root section")
                
            hardware = config["hardware"]
            
            # Validate network settings
            if "network" in hardware:
                network = hardware["network"]
                required = ["plc", "ssh"]
                for section in required:
                    if section not in network:
                        raise ConfigurationError(f"Missing required network section: {section}")
                        
            # Validate physical hardware
            if "physical" in hardware:
                physical = hardware["physical"]
                required = ["stage", "hardware_sets"]
                for section in required:
                    if section not in physical:
                        raise ConfigurationError(f"Missing required physical section: {section}")
                        
            # Validate safety settings
            if "safety" not in hardware:
                raise ConfigurationError("Missing safety settings")
                
        except Exception as e:
            raise ConfigurationError(f"Hardware config validation failed: {str(e)}")

    async def _validate_state_config(self, config: Dict[str, Any]) -> None:
        """Validate state config specifics."""
        try:
            if "state" not in config:
                raise ConfigurationError("Missing state root section")
                
            state = config["state"]
            
            # Validate initial state
            if "initial_state" not in state:
                raise ConfigurationError("Missing initial state")
                
            # Validate state transitions
            if "transitions" not in state:
                raise ConfigurationError("Missing state transitions")
                
            for state_name, state_def in state["transitions"].items():
                if "next_states" not in state_def:
                    raise ConfigurationError(f"Missing next states for {state_name}")
                    
        except Exception as e:
            raise ConfigurationError(f"State config validation failed: {str(e)}")

    async def _validate_application_config(self, config: Dict[str, Any]) -> None:
        """Validate application config specifics."""
        try:
            app_config = config.get("application", {})
            
            # Validate paths exist
            paths = app_config.get("paths", {})
            for path_name, path_value in paths.items():
                if isinstance(path_value, str):
                    path = Path(path_value)
                    if not path.exists():
                        logger.warning(f"Path does not exist: {path}")
                        
            # Validate services configuration
            services = app_config.get("services", {})
            for service_name, service_config in services.items():
                if not isinstance(service_config, dict):
                    raise ConfigurationError(f"Invalid service config for {service_name}")
                    
        except Exception as e:
            raise ConfigurationError(f"Application config validation failed: {str(e)}")

    async def _validate_tag_config(self, config: Dict[str, Any]) -> None:
        """Validate tag configuration."""
        try:
            if "tag_groups" not in config:
                raise ConfigurationError("Missing tag_groups root section")
            
            tag_groups = config["tag_groups"]
            
            # Validate each tag group
            for group_name, group_def in tag_groups.items():
                await self._validate_tag_group(group_name, group_def)
            
        except Exception as e:
            raise ConfigurationError(f"Tag config validation failed: {str(e)}")

    async def _validate_tag_group(self, group_name: str, group_def: Dict[str, Any]) -> None:
        """Validate a tag group definition."""
        try:
            # Validate each tag in group
            for tag_name, tag_def in group_def.items():
                # Check required fields
                if "access" not in tag_def:
                    raise ConfigurationError(f"Missing access type for tag: {group_name}.{tag_name}")
                
                # Validate mapped tags
                if tag_def.get("mapped", False):
                    if "plc_tag" not in tag_def:
                        raise ConfigurationError(f"Mapped tag missing plc_tag: {group_name}.{tag_name}")
                    
                # Validate tag type
                if "type" not in tag_def:
                    raise ConfigurationError(f"Missing type for tag: {group_name}.{tag_name}")
                
                # Validate scaling if present
                if "scaling" in tag_def:
                    if tag_def["scaling"] not in ["12bit_linear", "12bit_dac"]:
                        raise ConfigurationError(f"Invalid scaling type for tag: {group_name}.{tag_name}")
                    
                # Validate range if present
                if "range" in tag_def:
                    if not isinstance(tag_def["range"], list) or len(tag_def["range"]) != 2:
                        raise ConfigurationError(f"Invalid range for tag: {group_name}.{tag_name}")
                    
        except Exception as e:
            raise ConfigurationError(f"Tag group validation failed: {group_name} - {str(e)}")

    async def update_tag_mapping(self, tag_path: str, plc_tag: str) -> None:
        """Update PLC tag mapping."""
        try:
            # Parse tag path
            parts = tag_path.split('.')
            if len(parts) < 2:
                raise ConfigurationError("Invalid tag path format")
            
            group_name = parts[0]
            tag_name = '.'.join(parts[1:])
            
            # Get current tag config
            tag_config = self._configs.get("tags", {}).get("tag_groups", {})
            
            # Find and update tag
            if group_name not in tag_config:
                raise ConfigurationError(f"Tag group not found: {group_name}")
            
            group = tag_config[group_name]
            if tag_name not in group:
                raise ConfigurationError(f"Tag not found: {tag_path}")
            
            tag_def = group[tag_name]
            
            # Update mapping
            tag_def["mapped"] = True
            tag_def["plc_tag"] = plc_tag
            
            # Save updated config
            await self._save_config("tags", {"tag_groups": tag_config})
            
            # Notify update
            await self._message_broker.publish(
                "config/update",
                {
                    "type": "tag_mapping",
                    "tag": tag_path,
                    "plc_tag": plc_tag,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to update tag mapping: {str(e)}")