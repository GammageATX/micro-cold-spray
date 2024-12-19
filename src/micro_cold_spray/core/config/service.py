"""Simplified configuration service using Dynaconf."""

from dynaconf import Dynaconf, Validator
from fastapi import HTTPException, status
from loguru import logger

from micro_cold_spray.core.config.models.config_types import ConfigType, ConfigData, ConfigUpdate


class ConfigService:
    """Simplified configuration service using Dynaconf."""
    
    def __init__(self):
        """Initialize configuration service."""
        try:
            self.settings = Dynaconf(
                # Core settings files
                settings_files=[
                    # Base settings
                    'settings.yaml',
                    '.secrets.yaml',
                    
                    # System configs
                    'config/system/application.yaml',
                    'config/system/hardware.yaml',
                    'config/system/state.yaml',
                    
                    # Process configs
                    'config/process/process.yaml',
                    'config/process/actions.yaml',
                    'config/process/validations.yaml',
                    
                    # PLC configs
                    'config/plc/hardware_sets.yaml',
                    'config/plc/tags/control/*.yaml',   # Control tags
                    'config/plc/tags/hardware/*.yaml',  # Hardware tags
                    'config/plc/tags/system/*.yaml',    # System tags
                ],
                environments=True,
                env_switcher="MCS_ENV",
                load_dotenv=True,
                
                # Validation settings
                validate_on_update=True,
                validators=[
                    # System validators
                    Validator('system.application', must_exist=True),
                    Validator('system.hardware', must_exist=True),
                    Validator('system.state', must_exist=True),
                    
                    # Process validators
                    Validator('process.process', must_exist=True),
                    Validator('process.actions', must_exist=True),
                    Validator('process.validations', must_exist=True),
                    
                    # PLC validators
                    Validator('plc.hardware_sets', must_exist=True),
                    Validator('plc.tags.control', must_exist=True),
                    Validator('plc.tags.hardware', must_exist=True),
                    Validator('plc.tags.system', must_exist=True),
                ]
            )
            logger.info("Configuration service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize configuration service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Configuration service initialization failed: {str(e)}"
            )

    async def get_config(self, config_type: ConfigType) -> ConfigData:
        """Get configuration by type.
        
        Args:
            config_type: Type of configuration to retrieve
            
        Returns:
            Configuration data
            
        Raises:
            HTTPException: If configuration not found or invalid
        """
        try:
            # Map config types to their actual file structure
            config_map = {
                ConfigType.APPLICATION: "system.application",
                ConfigType.HARDWARE: "system.hardware",
                ConfigType.PROCESS: {
                    "process": "process.process",
                    "actions": "process.actions",
                    "validations": "process.validations"
                },
                ConfigType.STATE: "system.state",
                ConfigType.TAGS: {
                    "control": "plc.tags.control",
                    "hardware": "plc.tags.hardware",
                    "system": "plc.tags.system"
                }
            }
            
            # Get configuration from Dynaconf
            key = config_map.get(config_type)
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid config type: {config_type}"
                )
                
            # Handle composite configs (process and tags)
            if isinstance(key, dict):
                data = {}
                for section, path in key.items():
                    section_data = self.settings.get(path)
                    if section_data is None:
                        logger.warning(f"Section {section} not found in {config_type}")
                        continue
                    data[section] = section_data
            else:
                data = self.settings.get(key)
                
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Configuration not found: {config_type}"
                )
                
            return ConfigData(
                config_type=config_type,
                data=data
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get config {config_type}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get configuration: {str(e)}"
            )

    async def update_config(
        self,
        config_type: ConfigType,
        update: ConfigUpdate
    ) -> None:
        """Update configuration.
        
        Args:
            config_type: Type of configuration to update
            update: Update request with new data
            
        Raises:
            HTTPException: If update fails or validation fails
        """
        try:
            # Map config types to their actual file structure
            config_map = {
                ConfigType.APPLICATION: "system.application",
                ConfigType.HARDWARE: "system.hardware",
                ConfigType.PROCESS: {
                    "process": "process.process",
                    "actions": "process.actions",
                    "validations": "process.validations"
                },
                ConfigType.STATE: "system.state",
                ConfigType.TAGS: {
                    "control": "plc.tags.control",
                    "hardware": "plc.tags.hardware",
                    "system": "plc.tags.system"
                }
            }
            
            key = config_map.get(config_type)
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid config type: {config_type}"
                )
            
            # Handle composite configs (process and tags)
            if isinstance(key, dict):
                for section, path in key.items():
                    if section not in update.data:
                        logger.warning(f"Section {section} not found in update data")
                        continue
                    self.settings.update({
                        path: update.data[section]
                    })
            else:
                # Update single config
                self.settings.update({
                    key: update.data
                })
            
            # Write changes to file
            self.settings.write()
            
            logger.info(f"Updated configuration: {config_type}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update config {config_type}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update configuration: {str(e)}"
            )

    async def reload_config(self) -> None:
        """Reload all configurations from files."""
        try:
            self.settings.reload()
            logger.info("Configurations reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload configurations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reload configurations: {str(e)}"
            )

    def get_environment(self) -> str:
        """Get current environment name."""
        return self.settings.current_env.lower()

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.get_environment() == "production"
