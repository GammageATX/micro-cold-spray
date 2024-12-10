"""Motion control component."""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from ....core.exceptions import HardwareError
from ...infrastructure.config.config_manager import ConfigManager
from ...infrastructure.messaging.message_broker import MessageBroker
from ..validation.hardware_validator import HardwareValidator
from fastapi import APIRouter, HTTPException, Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/motion", tags=["motion"])


class MotionController:
    """Controls motion system through MessageBroker to TagManager."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager):
        """Initialize motion controller.

        Args:
            message_broker: MessageBroker instance for communication
            config_manager: ConfigManager instance for configuration
        """
        self._message_broker = message_broker
        self._config = config_manager
        self._hw_config = {}

        # Create hardware validator
        self._validator = HardwareValidator(
            message_broker=message_broker,
            config_manager=config_manager
        )

        # Make subscriptions async
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        """Initialize async components."""
        await self._load_config()
        await self._validator.initialize()
        await self._subscribe_to_commands()

    async def _load_config(self) -> None:
        """Load initial configuration."""
        try:
            config = await self._config.get_config('hardware')
            self._motion_config = config['hardware']['motion']
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def _subscribe_to_commands(self) -> None:
        """Subscribe to motion commands."""
        await self._message_broker.subscribe(
            "motion/command/move",
            self._handle_move_command)
        await self._message_broker.subscribe(
            "motion/command/xy_move",
            self._handle_xy_move_command)
        await self._message_broker.subscribe(
            "motion/command/set_home",
            self._handle_set_home)
        await self._message_broker.subscribe(
            "config/update/*",
            self._handle_config_update)

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
            # Convert to string and lowercase
            axis = str(data.get('axis', '')).lower()
            distance = float(data.get('distance', 0))  # Convert to float
            velocity = float(data.get('velocity', 0))  # Convert to float

            # Validate motion parameters
            valid, errors = await self._validator.validate_motion_limits(
                axis=axis,
                position=distance,
                velocity=velocity
            )

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Motion validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/motion/error",
                    {
                        "error": error_msg,
                        "context": "validation",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

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
                    "tag": f"motion_control.relative_move.{axis}_move.parameters.target",
                    "value": distance
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"motion_control.relative_move.{axis}_move.parameters.velocity",
                    "value": velocity
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"motion_control.relative_move.{axis}_move.parameters.acceleration",
                    "value": data.get('acceleration')
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"motion_control.relative_move.{axis}_move.parameters.deceleration",
                    "value": data.get('deceleration')
                }
            )

            # Trigger move
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"motion_control.relative_move.{axis}_move.trigger",
                    "value": True
                }
            )

            # Wait for move completion with timeout
            await self._wait_for_move_complete(plc_axis, distance, velocity)

        except Exception as e:
            logger.error(f"Move operation failed: {e}")
            await self._message_broker.publish(
                "hardware/motion/error",
                {
                    "error": str(e),
                    "context": "move_command",
                    "axis": axis,
                    "distance": distance,
                    "velocity": velocity,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise HardwareError("Move operation failed", "motion", {
                "axis": axis,
                "distance": distance,
                "velocity": velocity,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }) from e

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
                    f"Invalid parameter types: {str(e)}. Required: numbers for x_distance, y_distance, velocity")

            # Validate X motion
            valid_x, errors_x = await self._validator.validate_motion_limits(
                axis='x',
                position=x_distance,
                velocity=velocity
            )

            # Validate Y motion
            valid_y, errors_y = await self._validator.validate_motion_limits(
                axis='y',
                position=y_distance,
                velocity=velocity
            )

            # Combine validation results
            if not (valid_x and valid_y):
                errors = errors_x + errors_y
                error_msg = '; '.join(errors)
                logger.error(f"XY motion validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/motion/error",
                    {
                        "error": error_msg,
                        "context": "validation",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            # Set move parameters
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "motion_control.coordinated_move.xy_move.parameters.velocity",
                    "value": velocity
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "motion_control.coordinated_move.xy_move.parameters.ramps",
                    "value": ramps
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "motion_control.coordinated_move.xy_move.parameters.x_position",
                    "value": x_distance
                }
            )
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "motion_control.coordinated_move.xy_move.parameters.y_position",
                    "value": y_distance
                }
            )

            # Trigger move
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "motion_control.coordinated_move.xy_move.trigger",
                    "value": True
                }
            )

            # Calculate total distance for timeout
            distance = (x_distance**2 + y_distance**2)**0.5
            await self._wait_for_move_complete('XY', distance, velocity)

        except Exception as e:
            logger.error(f"XY move operation failed: {e}")
            await self._message_broker.publish(
                "hardware/motion/error",
                {
                    "error": str(e),
                    "context": "xy_move_command",
                    "x_distance": x_distance,
                    "y_distance": y_distance,
                    "velocity": velocity,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise HardwareError("XY move operation failed", "motion", {
                "x_distance": x_distance,
                "y_distance": y_distance,
                "velocity": velocity,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }) from e

    async def _handle_set_home(self, message: Dict[str, Any]) -> None:
        """Handle set home command."""
        try:
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "SetHome",
                    "value": True
                }
            )
        except Exception as e:
            logger.error(f"Set home operation failed: {e}")
            raise

    async def _handle_config_update(self, message: Dict[str, Any]) -> None:
        """Handle configuration update."""
        try:
            await self._load_config()
        except Exception as e:
            logger.error(f"Config update failed: {e}")
            raise

    async def _wait_for_move_complete(
            self,
            axis: str,
            distance: float,
            velocity: float) -> None:
        """Wait for move completion with timeout.

        Args:
            axis: Axis name ('X', 'Y', 'Z', or 'XY')
            distance: Move distance
            velocity: Move velocity

        Raises:
            TimeoutError: If move does not complete within timeout
        """
        # Calculate timeout based on distance and velocity
        # Add 50% margin for acceleration/deceleration
        timeout = (distance / velocity) * 1.5 if velocity > 0 else 5.0
        start_time = datetime.now()

        while True:
            # Check move status
            if axis == 'XY':
                response = await self._message_broker.request(
                    "tag/get",
                    {"tag": "motion_control.coordinated_move.xy_move.in_progress"}
                )
                if not response.get('value', True):
                    break
            else:
                response = await self._message_broker.request(
                    "tag/get",
                    {"tag": f"motion_control.relative_move.{axis.lower()}_move.in_progress"}
                )
                if not response.get('value', True):
                    break

            # Check timeout
            if (datetime.now() - start_time).total_seconds() > timeout:
                raise TimeoutError(f"{axis} move timeout after {timeout} seconds")

            await asyncio.sleep(0.1)  # Reduced polling interval


@router.post("/move")
async def move_axis(
    request: SingleAxisMoveRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Execute single axis move."""
    try:
        # Set move parameters
        base_path = f"motion_control.relative_move.{request.axis}_move"
        await plc_service.write_tag(f"{base_path}.parameters.target", request.distance)
        await plc_service.write_tag(f"{base_path}.parameters.velocity", request.velocity)
        
        # Trigger move
        await plc_service.write_tag(f"{base_path}.trigger", True)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/move/xy")
async def move_xy(
    request: CoordinatedMoveRequest,
    plc_service: PLCTagService = Depends(get_plc_service)
):
    """Execute coordinated XY move."""
    try:
        base_path = "motion_control.coordinated_move.xy_move"
        await plc_service.write_tag(f"{base_path}.parameters.x_position", request.x_distance)
        await plc_service.write_tag(f"{base_path}.parameters.y_position", request.y_distance)
        await plc_service.write_tag(f"{base_path}.parameters.velocity", request.velocity)
        await plc_service.write_tag(f"{base_path}.trigger", True)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ... other motion endpoints
