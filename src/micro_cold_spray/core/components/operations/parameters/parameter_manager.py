from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator
from ....exceptions import OperationError

class ParameterManager:
    """Manages process parameters and parameter sets."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        tag_manager: TagManager,
        message_broker: MessageBroker,
        process_validator: ProcessValidator
    ):
        """Initialize with required dependencies."""
        self._config = config_manager
        self._tag_manager = tag_manager
        self._message_broker = message_broker
        self._validator = process_validator
        self._parameters: Dict[str, Dict[str, Any]] = {}
        self._is_initialized = False
        
        logger.info("Parameter manager initialized")

    async def initialize(self) -> None:
        """Initialize parameter manager."""
        try:
            if self._is_initialized:
                return
                
            # Load parameters from config
            parameters_config = self._config.get_config('parameters')
            self._parameters = parameters_config.get('parameters', {})
            
            # Subscribe to parameter-related messages
            await self._message_broker.subscribe(
                "parameter/update",
                self._handle_parameter_update
            )
            
            self._is_initialized = True
            logger.info("Parameter manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize parameter manager")
            raise OperationError(f"Parameter manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown parameter manager."""
        try:
            # Save parameters to config if needed
            await self._config.update_config('parameters', {'parameters': self._parameters})
            self._is_initialized = False
            logger.info("Parameter manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during parameter manager shutdown")
            raise OperationError(f"Parameter manager shutdown failed: {str(e)}") from e

    async def _handle_parameter_update(self, data: Dict[str, Any]) -> None:
        """Handle parameter update messages."""
        try:
            command = data.get('command')
            if not command:
                raise ValueError("Missing command in parameter update")
                
            if command == 'update':
                await self.update_parameter_set(
                    data['set_name'],
                    data['updates']
                )
            elif command == 'create':
                await self.create_parameter_set(
                    data['set_name'],
                    data['parameters']
                )
                
        except Exception as e:
            logger.error(f"Error handling parameter update: {e}")
            await self._message_broker.publish(
                "parameter/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def get_parameter_set(self, set_name: str) -> Dict[str, Any]:
        """Get a parameter set by name."""
        try:
            if set_name not in self._parameters:
                raise ValueError(f"Parameter set not found: {set_name}")
                
            # Update access state through TagManager
            await self._tag_manager.set_tag(
                "parameters.access",
                {
                    "set_name": set_name,
                    "action": "read",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return self._parameters[set_name].copy()
            
        except Exception as e:
            logger.error(f"Error getting parameter set {set_name}: {e}")
            raise OperationError(f"Failed to get parameter set: {str(e)}") from e

    async def update_parameter_set(self, set_name: str, updates: Dict[str, Any]) -> None:
        """Update a parameter set."""
        try:
            if set_name not in self._parameters:
                raise ValueError(f"Parameter set not found: {set_name}")
                
            # Validate updates
            await self._validator.validate_parameters(set_name, updates)
            
            # Update parameters
            self._parameters[set_name].update(updates)
            
            # Update through config manager
            await self._config.update_config(
                'parameters',
                {'parameters': {set_name: self._parameters[set_name]}}
            )
            
            # Update state through TagManager
            await self._tag_manager.set_tag(
                "parameters.state",
                {
                    "set_name": set_name,
                    "status": "updated",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify system through MessageBroker
            await self._message_broker.publish(
                "parameters/updated",
                {
                    "set_name": set_name,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating parameter set {set_name}: {e}")
            raise OperationError(f"Failed to update parameter set: {str(e)}") from e

    def list_parameter_sets(self) -> Dict[str, Dict[str, Any]]:
        """Get all parameter sets."""
        return self._parameters.copy()