from typing import Dict, Any
import logging
import time
import asyncio

from ...infrastructure.messaging.message_broker import MessageBroker
from ...config.config_manager import ConfigManager
from ...components.process.validation.process_validator import ProcessValidator

logger = logging.getLogger(__name__)

class MotionController:
    """Controls motion system through MessageBroker to TagManager."""
    
    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
        """Initialize motion controller.
        
        Args:
            message_broker: MessageBroker instance for communication
            config_manager: ConfigManager instance for configuration
        """
        self._message_broker = message_broker
        self._config = config_manager
        
        # Create process validator
        self._validator = ProcessValidator(message_broker)
        
        # Load configs
        self._load_config()
        
        # Subscribe to motion commands
        self._message_broker.subscribe("motion/command/move", self._handle_move_command)
        self._message_broker.subscribe("motion/command/xy_move", self._handle_xy_move_command)
        self._message_broker.subscribe("motion/command/set_home", self._handle_set_home)
        self._message_broker.subscribe("config/update/hardware", self._handle_config_update)
        
        logger.info("Motion controller initialized")

    def _load_config(self) -> None:
        """Load initial configuration."""
        try:
            hw_config = self._config.get_config('hardware')
            self._motion_config = hw_config['hardware']['motion']
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def _handle_move_command(self, data: Dict[str, Any]) -> None:
        """Handle single axis relative move command.
        
        Args:
            data: Command data containing:
                axis: 'x', 'y', or 'z'
                distance: relative distance
                velocity: move velocity
                acceleration: optional acceleration
                deceleration: optional deceleration
        """
        try:
            # Validate parameters first
            validation_result = await self._validate_motion_parameters({
                'axis': data.get('axis'),
                'distance': data.get('distance'),
                'velocity': data.get('velocity')
            })
            
            if not validation_result['valid']:
                error_msg = '; '.join(validation_result['errors'])
                logger.error(f"Motion validation failed: {error_msg}")
                await self._message_broker.publish(
                    "motion/error",
                    {"error": f"Validation failed: {error_msg}"}
                )
                return

            # Validate required parameters
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict, got {type(data)}")
            
            axis = str(data.get('axis', '')).lower()  # Convert to string and lowercase
            distance = float(data.get('distance', 0))  # Convert to float
            velocity = float(data.get('velocity', 0))  # Convert to float
            
            if not axis or distance == 0 or velocity == 0:
                raise ValueError(
                    f"Missing required parameters. Got: axis={axis}, "
                    f"distance={distance}, velocity={velocity}"
                )

            # Map axis to PLC names
            plc_axis = {
                'x': 'X',
                'y': 'Y',
                'z': 'Z'
            }.get(axis)
            
            if not plc_axis:
                raise ValueError(f"Invalid axis: {axis}")

            # Set move parameters
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"{plc_axis}Axis.Target",
                    "value": distance
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"{plc_axis}Axis.Velocity",
                    "value": velocity
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"{plc_axis}Axis.Accel",
                    "value": data.get('acceleration')
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"{plc_axis}Axis.Decel",
                    "value": data.get('deceleration')
                }
            )

            # Trigger move
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"Move{plc_axis}",
                    "value": True
                }
            )

            # Wait for move completion with timeout
            await self._wait_for_move_complete(plc_axis, distance, velocity)

        except Exception as e:
            logger.error(f"Move operation failed: {e}")
            await self._message_broker.publish("motion/error", {"error": str(e)})
            raise

    async def _handle_xy_move_command(self, message: Dict[str, Any]) -> None:
        """Handle coordinated XY move command."""
        try:
            # Get and validate parameters
            try:
                x_distance = float(message.get('x_distance', 0))
                y_distance = float(message.get('y_distance', 0))
                velocity = float(message.get('velocity', 0))
                ramps = float(message.get('ramps', 0.1))
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid parameter types: {str(e)}. Required: numbers for "
                    "x_distance, y_distance, velocity"
                )
            
            # Validate values
            if x_distance == 0 and y_distance == 0:
                raise ValueError("At least one of x_distance or y_distance must be non-zero")
            if velocity <= 0:
                raise ValueError(f"Velocity must be positive, got {velocity}")

            # Set move parameters
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "XYMove.LINVelocity",
                    "value": velocity
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "XYMove.LINRamps",
                    "value": ramps
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "XYMove.XPosition",
                    "value": x_distance
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "XYMove.YPosition",
                    "value": y_distance
                }
            )

            # Trigger move
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "MoveXY",
                    "value": True
                }
            )

            # Calculate total distance for timeout
            # Now safe since we validated x_distance and y_distance are numbers
            distance = (x_distance**2 + y_distance**2)**0.5
            
            # Velocity is now guaranteed to be a positive float
            await self._wait_for_move_complete('xy', distance, velocity)

        except Exception as e:
            logger.error(f"XY move operation failed: {e}")
            await self._message_broker.publish("motion/error", {"error": str(e)})
            raise

    async def _handle_set_home(self, message: Dict[str, Any]) -> None:
        """Handle set home command (sets current position as 0,0,0)."""
        try:
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "SetHome",
                    "value": True
                }
            )
            logger.info("Home position set to current position")

        except Exception as e:
            logger.error(f"Set home operation failed: {e}")
            await self._message_broker.publish("motion/error", {"error": str(e)})
            raise

    async def _wait_for_move_complete(self, axis: str, distance: float, velocity: float) -> None:
        """Wait for move completion with timeout based on move parameters."""
        expected_time = abs(distance) / velocity if velocity > 0 else 0
        timeout = expected_time * 1.5 + 1.0  # Add buffer and 1 second base timeout
        
        start_time = time.time()
        
        # Wait for move to start (with timeout)
        while True:
            if (time.time() - start_time) > timeout:
                raise TimeoutError(f"{axis} move start timeout after {timeout:.1f}s")
                
            # Use correct tag names from tags.yaml
            tag_name = (
                f"motion_control.relative_move.{axis.lower()}_move.parameters.in_progress"
                if axis != 'xy' else
                "motion_control.coordinated_move.xy_move.parameters.in_progress"
            )
            
            response = await self._message_broker.request(
                "tag/get",
                {"tag": tag_name}
            )
            if response and response.get('value'):
                break
            await asyncio.sleep(0.01)
        
        # Wait for move to complete (with timeout)
        while True:
            if (time.time() - start_time) > timeout:
                raise TimeoutError(f"{axis} move completion timeout after {timeout:.1f}s")
                
            # Use correct tag names from tags.yaml
            tag_name = (
                f"motion_control.relative_move.{axis.lower()}_move.parameters.in_progress"
                if axis != 'xy' else
                "motion_control.coordinated_move.xy_move.parameters.in_progress"
            )
            
            response = await self._message_broker.request(
                "tag/get",
                {"tag": tag_name}
            )
            if response and not response.get('value'):
                break
            await asyncio.sleep(0.01)

    async def _handle_config_update(self, message: Dict[str, Any]) -> None:
        """Handle configuration updates."""
        try:
            if 'hardware' in message.get('new_config', {}):
                self._motion_config = message['new_config']['hardware']['motion']
        except Exception as e:
            logger.error(f"Config update failed: {e}")

    async def _validate_motion_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate motion parameters using ProcessValidator."""
        try:
            # Format parameters for validation
            validation_params = {
                "motion": {
                    "axis": params.get('axis'),
                    "distance": params.get('distance'),
                    "velocity": params.get('velocity'),
                    "acceleration": params.get('acceleration'),
                    "deceleration": params.get('deceleration')
                }
            }
            
            # Request validation
            response = await self._message_broker.request(
                "parameters/validate",
                {"parameters": validation_params}
            )
            
            if response is None:
                return {
                    "valid": False,
                    "errors": ["Validation request timeout"]
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error validating motion parameters: {e}")
            return {
                "valid": False,
                "errors": [str(e)]
            }
