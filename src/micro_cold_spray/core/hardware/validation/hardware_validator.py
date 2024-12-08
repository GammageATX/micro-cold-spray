"""Hardware validation component."""
from typing import Any, Dict, List, Optional, Tuple

from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker


class HardwareValidator:
    """Validates hardware operations and states."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager):
        """Initialize hardware validator.

        Args:
            message_broker: MessageBroker instance for communication
            config_manager: ConfigManager instance for configuration
        """
        self._message_broker = message_broker
        self._config = config_manager
        self._hw_config = {}

    async def initialize(self) -> None:
        """Load configuration and initialize validator."""
        config = await self._config.get_config('hardware')
        self._hw_config = config['hardware']

    async def validate_gas_flow(
            self,
            flow_type: str,
            value: float) -> Tuple[bool, List[str]]:
        """Validate gas flow setpoint against safety limits.

        Args:
            flow_type: Type of gas flow ('main' or 'feeder')
            value: Flow setpoint value

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []
        safety = self._hw_config['safety']['gas']

        if flow_type == 'main':
            limits = safety['main_flow']
            if value < limits['min']:
                errors.append(
                    f"Main flow too low: {value} (min {limits['min']})")
            elif value > limits['max']:
                errors.append(
                    f"Main flow too high: {value} (max {limits['max']})")

        elif flow_type == 'feeder':
            limits = safety['feeder_flow']
            if value < limits['min']:
                errors.append(
                    f"Feeder flow too low: {value} (min {limits['min']})")
            elif value > limits['max']:
                errors.append(
                    f"Feeder flow too high: {value} (max {limits['max']})")

        return len(errors) == 0, errors

    async def validate_motion_limits(
            self,
            axis: str,
            position: float,
            velocity: Optional[float] = None) -> Tuple[bool, List[str]]:
        """Validate motion parameters against safety limits.

        Args:
            axis: Motion axis ('x', 'y', or 'z')
            position: Target position
            velocity: Optional velocity value

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []
        stage = self._hw_config['physical']['stage']
        safety = self._hw_config['safety']['motion']

        # Position limits
        if axis in stage['dimensions']:
            limit = stage['dimensions'][axis]
            if abs(position) > limit:
                errors.append(
                    f"{axis.upper()} position {position} exceeds limit {limit}")

        # Velocity validation if provided
        if velocity is not None and safety['velocity_check']:
            # Add velocity validation logic here
            pass

        # Z-axis safety check
        if axis == 'x' or axis == 'y':
            if safety['require_safe_z_for_xy']:
                z_pos = await self._get_current_z_position()
                if z_pos < safety.get('safe_z_height', 10.0):
                    errors.append(
                        f"Z position {z_pos} below safe height for XY motion")

        return len(errors) == 0, errors

    async def validate_powder_system(
            self,
            hardware_set: int,
            frequency: Optional[float] = None,
            duty_cycle: Optional[float] = None) -> Tuple[bool, List[str]]:
        """Validate powder system parameters.

        Args:
            hardware_set: Hardware set number (1 or 2)
            frequency: Optional feeder frequency
            duty_cycle: Optional deagglomerator duty cycle

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []
        safety = self._hw_config['safety']['powder']

        if frequency is not None:
            limits = safety['feeder']['frequency']
            if frequency < limits['min']:
                errors.append(
                    f"Feeder frequency too low: {frequency} (min {limits['min']})")
            elif frequency > limits['max']:
                errors.append(
                    f"Feeder frequency too high: {frequency} (max {limits['max']})")

        if duty_cycle is not None:
            limits = safety['feeder']['deagglomerator']['duty_cycle']
            if duty_cycle < limits['min']:
                errors.append(
                    f"Duty cycle too low: {duty_cycle} (min {limits['min']})")
            elif duty_cycle > limits['max']:
                errors.append(
                    f"Duty cycle too high: {duty_cycle} (max {limits['max']})")

        return len(errors) == 0, errors

    async def validate_hardware_state(
            self,
            required_states: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate current hardware state against required states.

        Args:
            required_states: Dictionary of required hardware states

        Returns:
            Tuple of (valid: bool, errors: List[str])
        """
        errors = []

        # Get current states
        try:
            responses = await self._message_broker.request_multi([
                ("tag/get", {"tag": tag}) for tag in required_states.keys()
            ])

            for tag, required_value in required_states.items():
                current_value = responses.get(tag, {}).get('value')
                if current_value != required_value:
                    errors.append(
                        f"Invalid {tag} state: {current_value} != {required_value}")

        except Exception as e:
            errors.append(f"Failed to validate hardware state: {str(e)}")

        return len(errors) == 0, errors

    async def _get_current_z_position(self) -> float:
        """Get current Z axis position.

        Returns:
            Current Z position
        """
        response = await self._message_broker.request(
            "tag/get",
            {"tag": "motion.status.position.z"}
        )
        return float(response.get('value', 0.0))
