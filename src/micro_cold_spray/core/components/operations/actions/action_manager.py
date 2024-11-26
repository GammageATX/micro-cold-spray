"""Action management component."""
from typing import Dict, Any, Optional
import logging
import time

from ....infrastructure.messaging.message_broker import MessageBroker, Message, MessageType
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....hardware.controllers.motion_controller import MotionController
from ....hardware.controllers.equipment_controller import EquipmentController
from ....components.process.validation.process_validator import ProcessValidator

logger = logging.getLogger(__name__)

class ActionManager:
    """Manages execution of atomic actions."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        tag_manager: TagManager,
        motion_controller: MotionController,
        equipment_controller: EquipmentController,
        process_validator: ProcessValidator
    ):
        self._config = config_manager
        self._tag_manager = tag_manager
        self._motion = motion_controller
        self._equipment = equipment_controller
        self._validator = process_validator
        self._message_broker = MessageBroker()
        
        self._message_broker.subscribe("action_control", self._handle_action_control)
        self._message_broker.subscribe("action_control", self._handle_action_control)
        
        logger.info("Action manager initialized")

    async def _handle_action_control(self, message: Message) -> None:
        """Handle action control messages."""
        try:
            command = message.get('command')
            if command == 'execute':
                await self.execute_action(
                    message.data['action_type'],
                    message.data['parameters']
                )
        except Exception as e:
            logger.error(f"Error handling action control: {e}")
            # Use TagManager for state/status
            self._tag_manager.set_tag(
                "action.error",
                {
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
            # Use MessageBroker for system-wide error notification
            self._message_broker.publish(
                Message(
                    topic="action/error",
                    type=MessageType.ERROR,
                    data={"error": str(e)}
                )
            )

    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute an atomic action."""
        try:
            # Validate action
            await self._validator.validate_action(action_type, parameters)
            
            # Update state through TagManager
            self._tag_manager.set_tag(
                "action.status",
                {
                    "type": action_type,
                    "state": "running",
                    "parameters": parameters,
                    "timestamp": time.time()
                }
            )
            
            # Notify system through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="action/started",
                    type=MessageType.ACTION_STATUS,
                    data={
                        "type": action_type,
                        "parameters": parameters
                    }
                )
            )
            
            # Execute action
            if action_type == "move":
                await self._execute_move(parameters)
            elif action_type == "spray":
                await self._execute_spray(parameters)
            
            # Update completion through TagManager
            self._tag_manager.set_tag(
                "action.status",
                {
                    "type": action_type,
                    "state": "completed",
                    "parameters": parameters,
                    "timestamp": time.time()
                }
            )
            
            # Notify completion through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="action/completed",
                    type=MessageType.ACTION_STATUS,
                    data={
                        "type": action_type,
                        "parameters": parameters
                    }
                )
            )
            
        except Exception as e:
            # Update error state through TagManager
            self._tag_manager.set_tag(
                "action.status",
                {
                    "type": action_type,
                    "state": "error",
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
            
            # Notify error through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="action/error",
                    type=MessageType.ERROR,
                    data={
                        "type": action_type,
                        "error": str(e)
                    }
                )
            )
            raise

    async def _execute_move(self, parameters: Dict[str, Any]) -> None:
        """Execute a move action."""
        try:
            position = parameters.get("position")
            speed = parameters.get("speed")
            
            if not position or not speed:
                raise ValueError("Missing required move parameters")
                
            await self._motion.move_to(position, speed)
            
        except Exception as e:
            logger.error(f"Move action failed: {e}")
            raise

    async def _execute_spray(self, parameters: Dict[str, Any]) -> None:
        """Execute a spray action."""
        try:
            duration = parameters.get("duration")
            pressure = parameters.get("pressure")
            
            if not duration or not pressure:
                raise ValueError("Missing required spray parameters")
                
            await self._equipment.set_pressure(pressure)
            await self._equipment.start_spray()
            await time.sleep(duration)
            await self._equipment.stop_spray()
            
        except Exception as e:
            logger.error(f"Spray action failed: {e}")
            # Ensure spray is stopped on error
            await self._equipment.stop_spray()
            raise