"""Process management service."""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..base import BaseService
from ..data_collection.service import DataCollectionService, DataCollectionError
from ...core.infrastructure.config.config_manager import ConfigManager
from ...core.infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)

class ProcessError(Exception):
    """Base exception for process operations."""
    def __init__(self, message: str, context: Dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context if context is not None else {}

class ProcessService(BaseService):
    """Service for managing process operations."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        message_broker: MessageBroker,
        data_collection_service: DataCollectionService
    ):
        super().__init__(service_name="process")
        self._config_manager = config_manager
        self._message_broker = message_broker
        self._data_collection = data_collection_service
        
        # Process state
        self._active_sequence: Optional[str] = None
        self._sequence_step: int = 0
        self._process_lock = asyncio.Lock()
        
        # Configuration
        self._data_path: Optional[Path] = None
        self._config: Dict[str, Any] = {}
        
    async def start(self) -> None:
        """Start the process service."""
        await super().start()
        
        try:
            # Load configuration
            await self._load_config()
            
            # Set up event handlers
            await self._setup_event_handlers()
            
            logger.info("Process service started")
            
        except Exception as e:
            error_context = {
                "source": "process_service",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error("Failed to start process service", extra=error_context)
            await self._message_broker.publish("error", error_context)
            raise

    async def stop(self) -> None:
        """Stop the process service."""
        try:
            # Cancel any active sequence
            if self._active_sequence:
                await self.cancel_sequence()
                
            await super().stop()
            logger.info("Process service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping process service: {e}")
            raise

    async def _load_config(self) -> None:
        """Load process configuration."""
        try:
            # Load process config
            config = await self._config_manager.get_config("process")
            self._config = config.get("process", {})
            
            # Load application config for paths
            app_config = await self._config_manager.get_config("application")
            paths = app_config.get("application", {}).get("paths", {})
            
            # Set data paths
            root_path = Path(paths.get("data", {}).get("root", "data"))
            self._data_path = root_path
            
            logger.info("Process configuration loaded")
            
        except Exception as e:
            logger.error(f"Failed to load process configuration: {e}")
            raise

    async def _setup_event_handlers(self) -> None:
        """Set up handlers for process events."""
        try:
            # Subscribe to state changes
            await self._message_broker.subscribe(
                "state/change",
                self._handle_state_change
            )
            
            # Subscribe to hardware status
            await self._message_broker.subscribe(
                "hardware/status",
                self._handle_hardware_status
            )
            
            logger.info("Event handlers configured")
            
        except Exception as e:
            logger.error(f"Failed to set up event handlers: {e}")
            raise

    async def _handle_state_change(self, data: Dict[str, Any]) -> None:
        """Handle system state changes."""
        try:
            new_state = data.get("state")
            if new_state == "ERROR":
                # Cancel any active sequence
                if self._active_sequence:
                    await self.cancel_sequence()
                    
        except Exception as e:
            logger.error(f"Error handling state change: {e}")

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            status = data.get("status")
            if status == "disconnected":
                # Cancel any active sequence
                if self._active_sequence:
                    await self.cancel_sequence()
                    
        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")

    async def start_sequence(self, sequence_id: str) -> None:
        """
        Start executing a sequence.
        
        Args:
            sequence_id: ID of sequence to execute
            
        Raises:
            ProcessError: If sequence cannot be started
        """
        async with self._process_lock:
            try:
                if self._active_sequence:
                    raise ProcessError("Sequence already running")
                    
                # Start data collection first
                try:
                    collection_params = {
                        "sequence_id": sequence_id,
                        "data_path": str(self._data_path),
                        "config": self._config.get("data_collection", {})
                    }
                    await self._data_collection.start_collection(sequence_id, collection_params)
                    
                    # Wait for data collection to be ready
                    await self._data_collection.wait_collection_ready()
                    
                except DataCollectionError as e:
                    raise ProcessError(
                        "Failed to start data collection",
                        {"error": str(e), "context": e.context}
                    )
                    
                # Load sequence
                # Initialize execution
                # Start first step
                
                self._active_sequence = sequence_id
                self._sequence_step = 0
                
                # Notify sequence start
                await self._message_broker.publish(
                    "sequence/state",
                    {
                        "sequence_id": sequence_id,
                        "status": "started",
                        "step": 0,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                logger.info(f"Started sequence: {sequence_id}")
                
            except Exception as e:
                # Clean up data collection if it was started
                if self._data_collection.is_collecting:
                    try:
                        await self._data_collection.stop_collection()
                    except Exception as stop_error:
                        logger.error(f"Failed to stop data collection after sequence start error: {stop_error}")
                
                error_context = {
                    "sequence_id": sequence_id,
                    "error": str(e)
                }
                logger.error("Failed to start sequence", extra=error_context)
                raise ProcessError("Failed to start sequence", error_context)

    async def cancel_sequence(self) -> None:
        """
        Cancel the current sequence.
        
        Raises:
            ProcessError: If sequence cannot be cancelled
        """
        async with self._process_lock:
            try:
                if not self._active_sequence:
                    return
                    
                sequence_id = self._active_sequence
                
                # Stop execution
                # Clean up resources
                
                # Stop data collection
                try:
                    await self._data_collection.stop_collection()
                except DataCollectionError as e:
                    logger.error(f"Error stopping data collection during cancel: {e}")
                
                # Notify sequence cancelled
                await self._message_broker.publish(
                    "sequence/state",
                    {
                        "sequence_id": sequence_id,
                        "status": "cancelled",
                        "step": self._sequence_step,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                self._active_sequence = None
                self._sequence_step = 0
                
                logger.info(f"Cancelled sequence: {sequence_id}")
                
            except Exception as e:
                logger.error(f"Error cancelling sequence: {e}")
                raise ProcessError("Failed to cancel sequence", {"error": str(e)})

    async def _complete_sequence(self) -> None:
        """Handle sequence completion."""
        try:
            if not self._active_sequence:
                return
                
            sequence_id = self._active_sequence
            
            # Stop data collection
            try:
                await self._data_collection.stop_collection()
            except DataCollectionError as e:
                logger.error(f"Error stopping data collection during completion: {e}")
            
            # Notify sequence complete
            await self._message_broker.publish(
                "sequence/state",
                {
                    "sequence_id": sequence_id,
                    "status": "completed",
                    "step": self._sequence_step,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self._active_sequence = None
            self._sequence_step = 0
            
            logger.info(f"Completed sequence: {sequence_id}")
            
        except Exception as e:
            logger.error(f"Error completing sequence: {e}")

    @property
    def active_sequence(self) -> Optional[str]:
        """Get the currently active sequence ID."""
        return self._active_sequence

    @property
    def sequence_step(self) -> int:
        """Get the current sequence step."""
        return self._sequence_step
``` 