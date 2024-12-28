"""Tag cache service implementation."""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.communication.clients.mock import MockPLCClient
from micro_cold_spray.api.communication.clients.plc import PLCClient
from micro_cold_spray.api.communication.clients.ssh import SSHClient
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.models.equipment import (
    GasState, VacuumState, FeederState, NozzleState, EquipmentState,
    DeagglomeratorState, PressureState, MotionState, HardwareState,
    ProcessState, SafetyState
)
from micro_cold_spray.api.communication.models.motion import (
    Position, AxisStatus, SystemStatus
)


class TagCacheService:
    """Service for caching PLC tag values."""

    def __init__(self, config: Dict[str, Any], plc_client: Any, ssh_client: Optional[SSHClient], tag_mapping: TagMappingService):
        """Initialize tag cache service."""
        self._service_name = "tag_cache"
        self._version = "1.0.0"  # Will be updated from config
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._config = None
        self._plc_client = None
        self._ssh_client = None
        self._tag_mapping = None
        self._cache = {}
        self._state_cache = {}
        self._polling_task = None
        self._polling = None
        self._state_callbacks = []
        
        # Store constructor args for initialization
        self._init_config = config
        self._init_plc_client = plc_client
        self._init_ssh_client = ssh_client
        self._init_tag_mapping = tag_mapping
        
        logger.info(f"{self._service_name} service initialized")

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Load config and version
            self._config = self._init_config
            self._version = self._config["communication"]["services"]["tag_cache"]["version"]
            self._polling = self._config["communication"]["polling"]
            
            # Initialize components
            self._plc_client = self._init_plc_client
            self._ssh_client = self._init_ssh_client
            self._tag_mapping = self._init_tag_mapping
            
            # Initialize tag list from mapping service
            for tag in self._tag_mapping._tag_map.keys():
                self._cache[tag] = None
                
            # Initialize state cache
            self._state_cache = {
                "equipment": None,
                "gas": None,
                "vacuum": None,
                "feeder": None,
                "deagglomerator": None,
                "nozzle": None,
                "pressure": None,
                "motion": None,
                "hardware": None,
                "process": None,
                "safety": None
            }
                
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
                
            if not self._plc_client or not self._tag_mapping:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )
            
            # Connect to PLC client
            if isinstance(self._plc_client, MockPLCClient):
                await self._plc_client.connect()
            
            self._is_running = True
            self._start_time = datetime.now()
            self._polling_task = asyncio.create_task(self._poll_tags())
            logger.info(f"{self.service_name} service started")
            
        except Exception as e:
            self._is_running = False
            self._start_time = None
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )

            # 1. Stop external tasks
            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                self._polling_task = None

            # 2. Clear callbacks and caches
            self._state_callbacks.clear()
            self._cache.clear()
            self._state_cache.clear()
            
            # 3. Reset service state
            self._is_running = False
            self._start_time = None
            
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Check component health
            cache_ok = self.is_running and isinstance(self._cache, dict)
            plc_ok = self._plc_client is not None
            mapping_ok = self._tag_mapping is not None
            
            # Build component statuses
            components = {
                "cache": ComponentHealth(
                    status="ok" if cache_ok else "error",
                    error=None if cache_ok else "Cache not initialized"
                ),
                "plc_client": ComponentHealth(
                    status="ok" if plc_ok else "error",
                    error=None if plc_ok else "PLC client not initialized"
                ),
                "tag_mapping": ComponentHealth(
                    status="ok" if mapping_ok else "error",
                    error=None if mapping_ok else "Tag mapping not initialized"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={name: ComponentHealth(status="error", error=error_msg)
                            for name in ["cache", "plc_client", "tag_mapping"]}
            )

    def add_state_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Register callback for state changes."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Remove state change callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    async def get_tag(self, tag: str) -> Optional[Any]:
        """Get cached tag value."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
        return self._cache.get(tag)

    async def get_state(self, state_type: str) -> Optional[Any]:
        """Get cached state."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
        return self._state_cache.get(state_type)

    async def set_tag(self, tag: str, value: Any) -> None:
        """Set tag value."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )

        # Get tag mapping info
        tag_info = self._tag_mapping.get_tag_info(tag)
        if not tag_info:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag not found: {tag}"
            )

        # Check if tag is mapped to PLC or SSH
        is_plc_tag = "plc_tag" in tag_info
        is_ssh_tag = tag.startswith("ssh.")

        # Only write to client if we're not in mock mode
        if isinstance(self._plc_client, MockPLCClient):
            # In mock mode, just update the cache
            await self._plc_client.write_tag(tag, value)
            self._cache[tag] = value
            logger.debug(f"Set mock tag {tag} = {value}")
            return

        try:
            if is_plc_tag:
                # Write to PLC
                plc_tag = tag_info["plc_tag"]
                await self._plc_client.write_tag(plc_tag, value)
                self._cache[tag] = value
                logger.debug(f"Set PLC tag {plc_tag} = {value}")
            elif is_ssh_tag and self._ssh_client:
                # Write to SSH
                ssh_tag = tag.replace("ssh.", "")  # Remove ssh. prefix
                await self._ssh_client.write_tag(ssh_tag, value)
                self._cache[tag] = value
                logger.debug(f"Set SSH tag {ssh_tag} = {value}")
            else:
                # Internal tag - just update cache
                self._cache[tag] = value
                logger.debug(f"Set internal tag {tag} = {value}")

        except Exception as e:
            error_msg = f"Failed to set tag {tag} = {value}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    def get_all_tags(self) -> Dict[str, Any]:
        """Get all cached tag values."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )
        return self._cache.copy()

    async def _poll_tags(self) -> None:
        """Poll PLC tags and update cache."""
        prev_values = {}  # Track previous values to reduce logging
        
        while self._is_running:
            try:
                # Get all tag values
                for tag in self._cache.keys():
                    # Get tag mapping info
                    tag_info = self._tag_mapping.get_tag_info(tag)
                    if not tag_info:
                        continue

                    # Check if tag is mapped to PLC or SSH
                    is_plc_tag = "plc_tag" in tag_info
                    is_ssh_tag = tag.startswith("ssh.")

                    try:
                        if is_plc_tag:
                            # Read from PLC
                            plc_tag = tag_info["plc_tag"]
                            value = await self._plc_client.read_tag(plc_tag)
                        elif is_ssh_tag and self._ssh_client:
                            # Read from SSH
                            ssh_tag = tag.replace("ssh.", "")  # Remove ssh. prefix
                            value = await self._ssh_client.read_tag(ssh_tag)
                        else:
                            # Internal tag - skip polling
                            continue

                        # Only log and update if value changed
                        if tag not in prev_values or value != prev_values[tag]:
                            self._cache[tag] = value
                            prev_values[tag] = value
                            logger.debug(f"Updated tag {tag} = {value}")

                    except Exception as e:
                        logger.error(f"Error polling tag {tag}: {str(e)}")
                        continue

                # Update equipment states
                await self._update_equipment_states()
                        
                await asyncio.sleep(self._polling["interval"])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling tags: {str(e)}")
                await asyncio.sleep(1.0)  # Delay before retry

    async def _update_equipment_states(self) -> None:
        """Update cached equipment states."""
        try:
            # Update gas state
            gas_state = GasState(
                main_flow=self._cache.get("gas_control.main_flow.setpoint", 0),
                main_flow_measured=self._cache.get("gas_control.main_flow.measured", 0),
                feeder_flow=self._cache.get("gas_control.feeder_flow.setpoint", 0),
                feeder_flow_measured=self._cache.get("gas_control.feeder_flow.measured", 0),
                main_valve=self._cache.get("gas_control.main_valve.open", False),
                feeder_valve=self._cache.get("gas_control.feeder_valve.open", False)
            )
            
            # Update vacuum state
            vacuum_state = VacuumState(
                chamber_pressure=self._cache.get("vacuum.chamber_pressure", 0),
                gate_valve=self._cache.get("vacuum.gate_valve.open", False),
                mech_pump=self._cache.get("vacuum.mechanical_pump.start", False),
                booster_pump=self._cache.get("vacuum.booster_pump.start", False),
                vent_valve=self._cache.get("vacuum.vent_valve", False)
            )
            
            # Update feeder state (using feeder1 as primary)
            feeder_state = FeederState(
                running=self._cache.get("feeders.feeder1.running", False),
                frequency=self._cache.get("feeders.feeder1.frequency", 0)
            )
            
            # Update deagglomerator state (using deagg1 as primary)
            deagglomerator_state = DeagglomeratorState(
                duty_cycle=self._cache.get("deagglomerators.deagg1.duty_cycle", 0)
            )
            
            # Update nozzle state
            nozzle_state = NozzleState(
                active_nozzle=2 if self._cache.get("nozzle.select", False) else 1,
                shutter_open=self._cache.get("nozzle.shutter.open", False)
            )
            
            # Update pressure state
            pressure_state = PressureState(
                chamber=self._cache.get("vacuum.chamber_pressure", 0),
                feeder=self._cache.get("pressure.feeder_pressure", 0),
                main_supply=self._cache.get("pressure.main_supply_pressure", 0),
                nozzle=self._cache.get("nozzle.pressure", 0),
                regulator=self._cache.get("pressure.regulator_pressure", 0)
            )
            
            # Update motion state
            position = Position(
                x=self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.x_position", 0),
                y=self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.y_position", 0),
                z=self._cache.get("motion.motion_control.relative_move.z_move.parameters.position", 0)
            )
            
            # Get axis statuses
            x_status = AxisStatus(
                position=position.x,
                in_position=bool(self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.status", False)),
                moving=bool(self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.in_progress", False)),
                error=not bool(self._cache.get("interlocks.motion_ready", True)),
                homed=bool(self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.status", False))
            )
            
            y_status = AxisStatus(
                position=position.y,
                in_position=bool(self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.status", False)),
                moving=bool(self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.in_progress", False)),
                error=not bool(self._cache.get("interlocks.motion_ready", True)),
                homed=bool(self._cache.get("motion.motion_control.coordinated_move.xy_move.parameters.status", False))
            )
            
            z_status = AxisStatus(
                position=position.z,
                in_position=bool(self._cache.get("motion.motion_control.relative_move.z_move.parameters.status", False)),
                moving=bool(self._cache.get("motion.motion_control.relative_move.z_move.parameters.in_progress", False)),
                error=not bool(self._cache.get("interlocks.motion_ready", True)),
                homed=bool(self._cache.get("motion.motion_control.relative_move.z_move.parameters.status", False))
            )
            
            system_status = SystemStatus(
                x_axis=x_status,
                y_axis=y_status,
                z_axis=z_status,
                module_ready=bool(self._cache.get("interlocks.motion_ready", True))
            )
            
            motion_state = MotionState(
                position=position,
                status=system_status
            )
            
            # Update hardware state
            hardware_state = HardwareState(
                motion_enabled=bool(self._cache.get("interlocks.motion_ready", True)),
                plc_connected=bool(self._cache.get("system.plc_connected", True)),
                position_valid=bool(self._cache.get("motion.position_valid", True))
            )
            
            # Update process state
            process_state = ProcessState(
                gas_flow_stable=bool(self._cache.get("process.gas_flow_stable", True)),
                powder_feed_active=bool(self._cache.get("process.powder_feed_active", False)),
                process_ready=bool(self._cache.get("process.ready", True))
            )
            
            # Update safety state
            safety_state = SafetyState(
                emergency_stop=bool(self._cache.get("safety.emergency_stop", False)),
                interlocks_ok=bool(self._cache.get("safety.interlocks_ok", True)),
                limits_ok=bool(self._cache.get("safety.limits_ok", True))
            )

            # Update equipment state
            equipment_state = EquipmentState(
                gas=gas_state,
                vacuum=vacuum_state,
                feeder=feeder_state,
                deagglomerator=deagglomerator_state,
                nozzle=nozzle_state,
                pressure=pressure_state,
                motion=motion_state,
                hardware=hardware_state,
                process=process_state,
                safety=safety_state
            )
            
            # Update state cache
            self._state_cache["equipment"] = equipment_state
            self._state_cache["gas"] = gas_state
            self._state_cache["vacuum"] = vacuum_state
            self._state_cache["feeder"] = feeder_state
            self._state_cache["deagglomerator"] = deagglomerator_state
            self._state_cache["nozzle"] = nozzle_state
            self._state_cache["pressure"] = pressure_state
            self._state_cache["motion"] = motion_state
            self._state_cache["hardware"] = hardware_state
            self._state_cache["process"] = process_state
            self._state_cache["safety"] = safety_state
            
            # Notify state change callbacks
            for callback in self._state_callbacks:
                try:
                    callback("equipment", equipment_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error updating equipment states: {str(e)}")
