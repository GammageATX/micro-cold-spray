"""Action management component."""
from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....hardware.controllers.motion_controller import MotionController
from ....hardware.controllers.equipment_controller import EquipmentController
from ....components.process.validation.process_validator import ProcessValidator
from ....exceptions import OperationError

class ActionManager:
    """Manages execution of atomic actions."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        tag_manager: TagManager,
        message_broker: MessageBroker,
        motion_controller: MotionController,
        equipment_controller: EquipmentController,
        process_validator: ProcessValidator
    ):
        """Initialize with required dependencies."""
        self._config = config_manager
        self._tag_manager = tag_manager
        self._message_broker = message_broker
        self._motion = motion_controller
        self._equipment = equipment_controller
        self._validator = process_validator
        self._is_initialized = False
        
        logger.info("Action manager initialized")

    async def initialize(self) -> None:
        """Initialize action manager."""
        try:
            if self._is_initialized:
                return
                
            # Subscribe to action-related messages
            await self._message_broker.subscribe(
                "action/control",
                self._handle_action_control
            )
            
            self._is_initialized = True
            logger.info("Action manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize action manager")
            raise OperationError(f"Action manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown action manager."""
        try:
            self._is_initialized = False
            logger.info("Action manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during action manager shutdown")
            raise OperationError(f"Action manager shutdown failed: {str(e)}") from e

    async def _handle_action_control(self, data: Dict[str, Any]) -> None:
        """Handle action control messages."""
        try:
            command = data.get('command')
            if command == 'execute':
                await self.execute_action(
                    data['action_type'],
                    data['parameters']
                )
                
        except Exception as e:
            logger.error(f"Error handling action control: {e}")
            await self._message_broker.publish(
                "action/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute an action - either atomic or compound."""
        try:
            # Get action definition from config
            action_config = self._config.get_config("operation")["actions"]["standard_actions"]
            
            # Check if this is a compound action
            if action_type in action_config:
                await self._execute_compound_action(action_type, parameters)
            else:
                await self._execute_atomic_action(action_type, parameters)
                
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            await self._message_broker.publish(
                "action/error",
                {
                    "action": action_type,
                    "error": str(e),
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Action execution failed: {str(e)}") from e

    async def _execute_compound_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute a compound action from config."""
        try:
            action_def = self._config.get_config("operation")["actions"]["standard_actions"][action_type]
            
            # Execute each step in sequence
            for step in action_def["sequence"]:
                if step.startswith("wait_for"):
                    await self._wait_for_condition(step, parameters)
                else:
                    await self._execute_atomic_action(step, parameters)
                    
        except Exception as e:
            logger.error(f"Error executing compound action {action_type}: {e}")
            await self._message_broker.publish(
                "action/error",
                {
                    "action": action_type,
                    "step": step,
                    "error": str(e),
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Compound action execution failed: {str(e)}") from e

    async def _wait_for_condition(self, condition: str, parameters: Dict[str, Any]) -> None:
        """Wait for a condition to be met."""
        if condition == "wait_for_stability":
            # Get stability thresholds from config
            stability_config = self._config.get_config("hardware")["safety"]["gas"]
            
            while True:
                # Check relevant tags
                flow = await self._tag_manager.get_tag_value("gas.main.flow")
                pressure = await self._tag_manager.get_tag_value("gas.main.pressure")
                
                if self._check_stability(flow, pressure, stability_config):
                    break
                    
                await asyncio.sleep(0.1)

    async def _execute_atomic_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute an atomic action."""
        try:
            # Validate action
            await self._validator.validate_action(action_type, parameters)
            
            # Update state through TagManager
            await self._tag_manager.set_tag(
                "action.status",
                {
                    "type": action_type,
                    "state": "running",
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify system through MessageBroker
            await self._message_broker.publish(
                "action/started",
                {
                    "type": action_type,
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Execute action
            if action_type == "move":
                await self._execute_move(parameters)
            elif action_type == "spray":
                await self._execute_spray(parameters)
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
            # Update completion through TagManager
            await self._tag_manager.set_tag(
                "action.status",
                {
                    "type": action_type,
                    "state": "completed",
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify completion through MessageBroker
            await self._message_broker.publish(
                "action/completed",
                {
                    "type": action_type,
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            # Update error state through TagManager
            await self._tag_manager.set_tag(
                "action.status",
                {
                    "type": action_type,
                    "state": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify error through MessageBroker
            await self._message_broker.publish(
                "action/error",
                {
                    "type": action_type,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Action execution failed: {str(e)}") from e

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
            raise OperationError(f"Move action failed: {str(e)}") from e

    async def _execute_spray(self, parameters: Dict[str, Any]) -> None:
        """Execute a spray action."""
        try:
            duration = parameters.get("duration")
            pressure = parameters.get("pressure")
            
            if not duration or not pressure:
                raise ValueError("Missing required spray parameters")
                
            await self._equipment.set_pressure(pressure)
            await self._equipment.start_spray()
            await asyncio.sleep(duration)
            await self._equipment.stop_spray()
            
        except Exception as e:
            logger.error(f"Spray action failed: {e}")
            # Ensure spray is stopped on error
            try:
                await self._equipment.stop_spray()
            except Exception as stop_error:
                logger.error(f"Failed to stop spray on error: {stop_error}")
            raise OperationError(f"Spray action failed: {str(e)}") from e