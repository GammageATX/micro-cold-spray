from typing import Dict, Any, Optional
import logging
import time

from ....infrastructure.messaging.message_broker import MessageBroker, Message, MessageType
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator

logger = logging.getLogger(__name__)

class ParameterError(Exception):
    """Base class for parameter-related errors."""
    pass

class ParameterManager:
    """Manages process parameters and parameter sets."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        tag_manager: TagManager,
        process_validator: ProcessValidator
    ):
        self._config = config_manager
        self._tag_manager = tag_manager
        self._validator = process_validator
        self._message_broker = MessageBroker()
        
        # Only subscribe to parameter-related messages
        self._message_broker.subscribe("parameter_update", self._handle_parameter_update)
        
        logger.info("Parameter manager initialized")

    async def _handle_parameter_update(self, message: Message) -> None:
        """Handle parameter update messages."""
        try:
            command = message.get('command')
            if command == 'update':
                await self.update_parameter_set(
                    message.data['set_name'],
                    message.data['updates']
                )
            elif command == 'create':
                await self.create_parameter_set(
                    message.data['set_name'],
                    message.data['parameters']
                )
        except Exception as e:
            logger.error(f"Error handling parameter update: {e}")
            # Use TagManager for error state
            self._tag_manager.set_tag(
                "parameters.error",
                {
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
            # Use MessageBroker for system-wide notification
            self._message_broker.publish(
                Message(
                    topic="parameters/error",
                    type=MessageType.ERROR,
                    data={"error": str(e)}
                )
            )

    def get_parameter_set(self, set_name: str) -> Dict[str, Any]:
        """Get a parameter set by name."""
        try:
            if set_name not in self._parameters:
                raise ValueError(f"Parameter set not found: {set_name}")
                
            # Update access state through TagManager
            self._tag_manager.set_tag(
                "parameters.access",
                {
                    "set_name": set_name,
                    "action": "read",
                    "timestamp": time.time()
                }
            )
            
            return self._parameters[set_name].copy()
            
        except Exception as e:
            logger.error(f"Error getting parameter set {set_name}: {e}")
            raise

    async def update_parameter_set(self, set_name: str, updates: Dict[str, Any]) -> None:
        """Update a parameter set."""
        try:
            if set_name not in self._parameters:
                raise ValueError(f"Parameter set not found: {set_name}")
                
            # Validate updates
            await self._validator.validate_parameters(set_name, updates)
            
            # Update parameters through ConfigManager
            self._config.update_config(
                'operation',
                {'parameters': {set_name: updates}}
            )
            
            # Update state through TagManager
            self._tag_manager.set_tag(
                "parameters.state",
                {
                    "set_name": set_name,
                    "status": "updated",
                    "timestamp": time.time()
                }
            )
            
            # Notify system through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="parameters/updated",
                    type=MessageType.PARAMETER_UPDATE,
                    data={
                        "set_name": set_name,
                        "updates": updates
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error updating parameter set {set_name}: {e}")
            raise

    def list_parameter_sets(self) -> Dict[str, Dict[str, Any]]:
        """Get all parameter sets."""
        return self._parameters.copy()