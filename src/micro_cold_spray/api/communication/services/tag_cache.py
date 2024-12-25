"""Tag cache service implementation."""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.clients.mock import MockPLCClient
from micro_cold_spray.api.communication.clients.plc import PLCClient
from micro_cold_spray.api.communication.clients.ssh import SSHClient
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.models.equipment import (
    GasState, VacuumState, FeederState, NozzleState, EquipmentState
)


class TagCacheService:
    """Service for caching PLC tag values."""

    def __init__(self, plc_client: Any, ssh_client: Optional[SSHClient], tag_mapping: TagMappingService):
        """Initialize tag cache service.
        
        Args:
            plc_client: PLC client (mock or real)
            ssh_client: SSH client (optional)
            tag_mapping: Tag mapping service
        """
        self._plc_client = plc_client
        self._ssh_client = ssh_client
        self._tag_mapping = tag_mapping
        self._cache: Dict[str, Any] = {}
        self._state_cache: Dict[str, Any] = {}
        self._polling_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._start_time = None
        self._service_name = "tag_cache"
        self._version = "1.0.0"
        self._initialized = False
        
        # Get polling config from tag mapping service
        self._polling = tag_mapping._config["communication"]["polling"]
        
        # State change callbacks
        self._state_callbacks: List[Callable[[str, Any], None]] = []
        
        logger.info("\n Tag cache service initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0

    async def initialize(self) -> None:
        """Initialize tag cache service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if self._initialized:
                logger.debug("Tag cache service already initialized")
                return
            
            # Initialize tag list from mapping service
            for tag in self._tag_mapping._tag_map.keys():
                self._cache[tag] = None
                
            # Initialize state cache
            self._state_cache = {
                "equipment": None,
                "gas": None,
                "vacuum": None,
                "feeder1": None,
                "feeder2": None,
                "nozzle": None
            }
                
            self._initialized = True
            logger.info("Tag cache service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start tag polling.
        
        Raises:
            HTTPException: If startup fails
        """
        try:
            if self.is_running:
                logger.debug("Tag cache service already running")
                return
                
            if not self._initialized:
                await self.initialize()
            
            self._is_running = True
            self._start_time = datetime.now()
            self._polling_task = asyncio.create_task(self._poll_tags())
            logger.info("Tag cache service started")
            
        except Exception as e:
            error_msg = f"Failed to start tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop tag polling.
        
        Raises:
            HTTPException: If shutdown fails
        """
        try:
            if not self.is_running:
                return
            
            self._is_running = False
            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                self._polling_task = None
            
            self._start_time = None
            self._cache.clear()
            self._state_cache.clear()
            self._initialized = False
            logger.info("Tag cache service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

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
                main_flow=self._cache.get("gas_control.main_flow.measured", 0),
                feeder_flow=self._cache.get("gas_control.feeder_flow.measured", 0),
                main_valve=self._cache.get("valve_control.main_gas", False),
                feeder_valve=self._cache.get("valve_control.feeder_gas", False)
            )
            
            # Update vacuum state
            vacuum_state = VacuumState(
                chamber_pressure=self._cache.get("pressure.chamber_pressure", 0),
                gate_valve=self._cache.get("valve_control.gate_valve.open", False),
                mech_pump=self._cache.get("vacuum_control.mechanical_pump.start", False),
                booster_pump=self._cache.get("vacuum_control.booster_pump.start", False)
            )
            
            # Update feeder states
            feeder1_state = FeederState(
                running=self._cache.get("ssh.P10", 0) == 1,
                frequency=self._cache.get("gas_control.hardware_sets.set1.feeder.frequency", 0)
            )
            
            feeder2_state = FeederState(
                running=self._cache.get("ssh.P110", 0) == 1,
                frequency=self._cache.get("gas_control.hardware_sets.set2.feeder.frequency", 0)
            )
            
            # Update nozzle state
            nozzle_state = NozzleState(
                active_nozzle=2 if self._cache.get("gas_control.hardware_sets.nozzle_select", False) else 1,
                shutter_open=self._cache.get("relay_control.shutter", False),
                pressure=self._cache.get("pressure.nozzle_pressure", 0)
            )
            
            # Create complete equipment state
            equipment_state = EquipmentState(
                gas=gas_state,
                vacuum=vacuum_state,
                feeder1=feeder1_state,
                feeder2=feeder2_state,
                nozzle=nozzle_state
            )
            
            # Update state cache and notify callbacks if changed
            if equipment_state != self._state_cache["equipment"]:
                self._state_cache.update({
                    "equipment": equipment_state,
                    "gas": gas_state,
                    "vacuum": vacuum_state,
                    "feeder1": feeder1_state,
                    "feeder2": feeder2_state,
                    "nozzle": nozzle_state
                })
                
                # Notify state change callbacks
                for callback in self._state_callbacks:
                    try:
                        callback("equipment", equipment_state)
                    except Exception as e:
                        logger.error(f"Error in state change callback: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error updating equipment states: {str(e)}")

    def add_state_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Add state change callback.
        
        Args:
            callback: Function to call when state changes
        """
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Remove state change callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    async def get_tag(self, tag: str) -> Optional[Any]:
        """Get cached tag value.
        
        Args:
            tag: Tag name
            
        Returns:
            Tag value if found, None otherwise
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Tag cache service not running"
            )
        return self._cache.get(tag)

    async def get_state(self, state_type: str) -> Optional[Any]:
        """Get cached state.
        
        Args:
            state_type: Type of state to get (equipment, gas, vacuum, etc.)
            
        Returns:
            State if found, None otherwise
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Tag cache service not running"
            )
        return self._state_cache.get(state_type)

    async def set_tag(self, tag: str, value: Any) -> None:
        """Set tag value.
        
        Args:
            tag: Tag name
            value: Value to set
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Tag cache service not running"
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
        """Get all cached tag values.
        
        Returns:
            Dict mapping tag names to values
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Tag cache service not running"
            )
        return self._cache.copy()

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status dictionary
        """
        try:
            return {
                "status": "ok" if self.is_running else "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": self.is_running,
                "uptime": self.uptime,
                "error": None if self.is_running else "Service not running",
                "tag_count": len(self._cache),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = f"Failed to get health status: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": False,
                "uptime": 0,
                "error": error_msg,
                "tag_count": 0,
                "timestamp": datetime.now().isoformat()
            }
