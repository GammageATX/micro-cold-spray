"""Equipment control component."""
from typing import Dict, Any
import logging
import time
import asyncio
from datetime import datetime

from ...infrastructure.messaging.message_broker import MessageBroker
from ...infrastructure.config.config_manager import ConfigManager
from ...exceptions import HardwareError

logger = logging.getLogger(__name__)

class EquipmentController:
    """Controls equipment through MessageBroker to TagManager."""
    
    def __init__(self, config_manager: ConfigManager):
        self._config = config_manager
        self._message_broker = MessageBroker()
        
        # Load configs
        self._load_config()
        
        # Subscribe to equipment commands
        self._message_broker.subscribe("equipment/gas/flow", self._handle_gas_flow)
        self._message_broker.subscribe("equipment/gas/valve", self._handle_gas_valve)
        self._message_broker.subscribe("equipment/vacuum/pump", self._handle_pump)
        self._message_broker.subscribe("equipment/vacuum/valve", self._handle_vacuum_valve)
        self._message_broker.subscribe("equipment/feeder", self._handle_feeder)
        self._message_broker.subscribe("equipment/deagglomerator", self._handle_deagglomerator)
        self._message_broker.subscribe("equipment/nozzle", self._handle_nozzle)
        self._message_broker.subscribe("equipment/shutter", self._handle_shutter)
        self._message_broker.subscribe("config/update/hardware", self._handle_config_update)
        
        logger.info("Equipment controller initialized")

    def _load_config(self) -> None:
        """Load initial configuration."""
        try:
            hw_config = self._config.get_config('hardware')['hardware']
            self._hw_config = hw_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def _handle_gas_flow(self, message: Dict[str, Any]) -> None:
        """Handle gas flow setpoints."""
        try:
            flow_type = message.get('type')
            value = message.get('value')
            
            # Get safety limits from config
            safety_limits = self._hw_config["safety"]["gas"]
            
            # Validate against limits
            if flow_type == "main":
                if value < safety_limits["main_pressure"]["min"]:
                    raise ValueError(
                        f"Main flow too low: {value} PSI (min {safety_limits['main_pressure']['min']} PSI)"
                    )
            elif flow_type == "feeder":
                if value < safety_limits["feeder_pressure"]["min"]:
                    raise ValueError(
                        f"Feeder flow too low: {value} PSI (min {safety_limits['feeder_pressure']['min']} PSI)"
                    )

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
            raise HardwareError("Gas flow control failed", "gas_control", {
                "flow_type": flow_type,
                "value": value,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_gas_valve(self, message: Dict[str, Any]) -> None:
        """Handle gas valve control."""
        try:
            valve = message.get('valve')  # 'main' or 'feeder'
            state = message.get('state')  # bool
            
            if not valve or state is None:
                raise ValueError("Missing required parameters")

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

            # Send momentary signal
            tag = f"valve_control.{pump}_pump.{action}"
            await self._set_momentary_tag(tag)

            # Monitor status change with timeout
            start_time = time.time()
            timeout = 5.0  # 5 second timeout
            
            while (time.time() - start_time) < timeout:
                response = await self._message_broker.request(  # Changed from publish to request
                    "tag/get",
                    {"tag": f"valve_control.{pump}_pump.running"}
                )
                if response and response.get('value') == (action == 'start'):
                    break
                await asyncio.sleep(0.1)  # Changed from time.sleep
            else:
                raise TimeoutError(f"Pump {action} timeout")

        except Exception as e:
            logger.error(f"Pump control failed: {e}")
            raise

    async def _handle_vacuum_valve(self, message: Dict[str, Any]) -> None:
        """Handle vacuum valve control."""
        try:
            valve = message.get('valve')  # 'gate' or 'vent'
            position = message.get('position')  # For gate: 'partial'/'open', For vent: bool

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
            
            await self._message_broker.publish(
                "tag/set",
                {
                    "tag": "relay_control.shutter",
                    "value": state
                }
            )

        except Exception as e:
            logger.error(f"Shutter control failed: {e}")
            raise

    async def _set_momentary_tag(self, tag: str, pulse_time: float = 0.5) -> None:
        """Set a tag momentarily then reset it."""
        try:
            await self._message_broker.publish("tag/set", {"tag": tag, "value": True})
            await asyncio.sleep(pulse_time)  # Changed from time.sleep
            await self._message_broker.publish("tag/set", {"tag": tag, "value": False})
        except Exception as e:
            logger.error(f"Error setting momentary tag {tag}: {e}")
            raise

    async def _handle_config_update(self, message: Dict[str, Any]) -> None:
        """Handle configuration updates."""
        try:
            new_config = message.get('new_config', {})
            if 'hardware' in new_config:
                self._hw_config = new_config['hardware']
        except Exception as e:
            logger.error(f"Config update failed: {e}")