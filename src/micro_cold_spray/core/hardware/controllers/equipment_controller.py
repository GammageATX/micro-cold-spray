"""Equipment control component."""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from ...exceptions import HardwareError
from ...infrastructure.config.config_manager import ConfigManager
from ...infrastructure.messaging.message_broker import MessageBroker
from ..validation.hardware_validator import HardwareValidator

logger = logging.getLogger(__name__)


class EquipmentController:
    """Controls equipment through MessageBroker to TagManager."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize equipment controller.

        Args:
            config_manager: ConfigManager instance for configuration
        """
        self._config = config_manager
        self._message_broker = MessageBroker()
        self._hw_config = {}

        # Create hardware validator
        self._validator = HardwareValidator(
            message_broker=self._message_broker,
            config_manager=config_manager
        )

        # Initialize async
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
            self._hw_config = config['hardware']
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def _subscribe_to_commands(self) -> None:
        """Subscribe to equipment commands."""
        await self._message_broker.subscribe(
            "equipment/gas/flow", self._handle_gas_flow)
        await self._message_broker.subscribe(
            "equipment/gas/valve", self._handle_gas_valve)
        await self._message_broker.subscribe(
            "equipment/vacuum/pump", self._handle_pump)
        await self._message_broker.subscribe(
            "equipment/vacuum/valve", self._handle_vacuum_valve)
        await self._message_broker.subscribe(
            "equipment/feeder", self._handle_feeder)
        await self._message_broker.subscribe(
            "equipment/deagglomerator", self._handle_deagglomerator)
        await self._message_broker.subscribe(
            "equipment/nozzle", self._handle_nozzle)
        await self._message_broker.subscribe(
            "equipment/shutter", self._handle_shutter)
        await self._message_broker.subscribe(
            "config/update/*", self._handle_config_update)

        logger.info("Equipment controller initialized")

    async def _handle_gas_flow(self, message: Dict[str, Any]) -> None:
        """Handle gas flow setpoints."""
        try:
            flow_type = message.get('type')
            value = message.get('value')

            # Validate gas flow
            valid, errors = await self._validator.validate_gas_flow(
                flow_type=flow_type,
                value=value
            )

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Gas flow validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "gas_flow",
                        "flow_type": flow_type,
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"gas_control.{flow_type}_flow.setpoint",
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Gas flow control failed: {e}")
            await self._message_broker.publish(
                "hardware/plc/error",
                {
                    "error": str(e),
                    "context": "gas_flow",
                    "flow_type": flow_type,
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise HardwareError("Gas flow control failed", "gas_control", {
                "flow_type": flow_type,
                "value": value,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }) from e

    async def _handle_gas_valve(self, message: Dict[str, Any]) -> None:
        """Handle gas valve control."""
        try:
            valve = message.get('valve')  # 'main' or 'feeder'
            state = message.get('state')  # bool

            if not valve or state is None:
                raise ValueError("Missing required parameters")

            # Validate valve state
            valid, errors = await self._validator.validate_hardware_state({
                f"valve_control.{valve}_gas": state
            })

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Gas valve validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "gas_valve",
                        "valve": valve,
                        "state": state,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"valve_control.{valve}_gas",
                    "value": state
                }
            )

        except Exception as e:
            logger.error(f"Gas valve control failed: {e}")
            raise

    async def _handle_pump(self, message: Dict[str, Any]) -> None:
        """Handle vacuum pump control (momentary signals)."""
        try:
            pump = message.get('pump')  # 'mechanical' or 'booster'
            action = message.get('action')  # 'start' or 'stop'

            # Validate pump state
            valid, errors = await self._validator.validate_hardware_state({
                f"valve_control.{pump}_pump.running": (action == 'start')
            })

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Pump validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "pump",
                        "pump": pump,
                        "action": action,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            # Send momentary signal
            tag = f"valve_control.{pump}_pump.{action}"
            await self._set_momentary_tag(tag)

            # Monitor status change with timeout
            start_time = datetime.now()
            timeout = 5.0  # 5 second timeout

            while (datetime.now() - start_time).total_seconds() < timeout:
                response = await self._message_broker.request(
                    "tag/get",
                    {"tag": f"valve_control.{pump}_pump.running"}
                )
                if response and response.get('value') == (action == 'start'):
                    break
                await asyncio.sleep(0.1)
            else:
                raise TimeoutError(f"Pump {action} timeout")

        except Exception as e:
            logger.error(f"Pump control failed: {e}")
            raise

    async def _handle_vacuum_valve(self, message: Dict[str, Any]) -> None:
        """Handle vacuum valve control."""
        try:
            valve = message.get('valve')  # 'gate' or 'vent'
            # For gate: 'partial'/'open', For vent: bool
            position = message.get('position')

            # Validate valve state
            if valve == 'gate':
                valid, errors = await self._validator.validate_hardware_state({
                    f"valve_control.gate_valve.{position}": True
                })
            else:  # vent valve
                valid, errors = await self._validator.validate_hardware_state({
                    "valve_control.vent": position
                })

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Vacuum valve validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "vacuum_valve",
                        "valve": valve,
                        "position": position,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            if valve == 'gate':
                await self._message_broker.publish(
                    "tag/set",
                    {
                        "tag": f"valve_control.gate_valve.{position}",
                        "value": True
                    }
                )
            else:  # vent valve
                await self._message_broker.publish(
                    "tag/set",
                    {
                        "tag": "valve_control.vent",
                        "value": position
                    }
                )

        except Exception as e:
            logger.error(f"Vacuum valve control failed: {e}")
            raise

    async def _handle_feeder(self, message: Dict[str, Any]) -> None:
        """Handle powder feeder control."""
        try:
            hardware_set = message.get('hardware_set', 1)
            frequency = message.get('frequency')

            # Validate feeder parameters
            valid, errors = await self._validator.validate_powder_system(
                hardware_set=hardware_set,
                frequency=frequency
            )

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Feeder validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "feeder",
                        "hardware_set": hardware_set,
                        "frequency": frequency,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": f"hardware_sets.set{hardware_set}.feeder.frequency",
                    "value": frequency
                }
            )

        except Exception as e:
            logger.error(f"Feeder control failed: {e}")
            raise

    async def _handle_deagglomerator(self, message: Dict[str, Any]) -> None:
        """Handle deagglomerator control."""
        try:
            hardware_set = message.get('hardware_set', 1)
            duty = message.get('duty')
            freq = message.get('frequency')

            # Validate deagglomerator parameters
            valid, errors = await self._validator.validate_powder_system(
                hardware_set=hardware_set,
                duty_cycle=duty
            )

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Deagglomerator validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "deagglomerator",
                        "hardware_set": hardware_set,
                        "duty": duty,
                        "frequency": freq,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            if duty is not None:
                await self._message_broker.publish(
                    "tag/set",
                    {
                        "tag": f"hardware_sets.set{hardware_set}.deagglomerator.duty_cycle",
                        "value": duty
                    }
                )

            if freq is not None:
                await self._message_broker.publish(
                    "tag/set",
                    {
                        "tag": f"hardware_sets.set{hardware_set}.deagglomerator.frequency",
                        "value": freq
                    }
                )

        except Exception as e:
            logger.error(f"Deagglomerator control failed: {e}")
            raise

    async def _handle_nozzle(self, message: Dict[str, Any]) -> None:
        """Handle nozzle selection."""
        try:
            nozzle = message.get('nozzle')  # 1 or 2

            # Validate nozzle selection
            valid, errors = await self._validator.validate_hardware_state({
                "hardware_sets.nozzle_select": nozzle == 2  # false=1, true=2
            })

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Nozzle validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "nozzle",
                        "nozzle": nozzle,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "hardware_sets.nozzle_select",
                    "value": nozzle == 2  # false=1, true=2
                }
            )

        except Exception as e:
            logger.error(f"Nozzle selection failed: {e}")
            raise

    async def _handle_shutter(self, message: Dict[str, Any]) -> None:
        """Handle shutter control."""
        try:
            state = message.get('state')  # bool

            # Validate shutter state
            valid, errors = await self._validator.validate_hardware_state({
                "hardware_sets.shutter": state
            })

            if not valid:
                error_msg = '; '.join(errors)
                logger.error(f"Shutter validation failed: {error_msg}")
                await self._message_broker.publish(
                    "hardware/plc/error",
                    {
                        "error": error_msg,
                        "context": "shutter",
                        "state": state,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "hardware_sets.shutter",
                    "value": state
                }
            )

        except Exception as e:
            logger.error(f"Shutter control failed: {e}")
            raise

    async def _handle_config_update(self, message: Dict[str, Any]) -> None:
        """Handle configuration update."""
        try:
            await self._load_config()
        except Exception as e:
            logger.error(f"Config update failed: {e}")
            raise

    async def _set_momentary_tag(self, tag: str) -> None:
        """Set momentary tag value.

        Args:
            tag: Tag to set momentarily
        """
        try:
            # Set tag true
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": tag,
                    "value": True
                }
            )

            # Wait briefly
            await asyncio.sleep(0.1)

            # Set tag false
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": tag,
                    "value": False
                }
            )

        except Exception as e:
            logger.error(f"Failed to set momentary tag {tag}: {e}")
            raise
