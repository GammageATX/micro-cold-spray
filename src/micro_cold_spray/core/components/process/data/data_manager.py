from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from pathlib import Path
import json
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager
from ....exceptions import OperationError

class DataManager:
    """Manages process data collection and storage."""
    
    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._process_data: Dict[str, Dict[str, Any]] = {}
        self._data_path = Path("data/process")
        self._current_user: Optional[str] = None
        self._cancelled = False
        self._is_initialized = False
        
        logger.info("Data manager initialized")

    async def initialize(self) -> None:
        """Initialize data manager."""
        try:
            if self._is_initialized:
                return

            # Ensure data directory exists
            self._data_path.mkdir(parents=True, exist_ok=True)
            
            # Subscribe to tag updates for data collection
            await self._message_broker.subscribe(
                "tag/update",
                self._handle_tag_update
            )
            
            self._is_initialized = True
            logger.info("Data manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize data manager")
            raise OperationError(f"Data manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown data manager."""
        try:
            # Save any pending data
            if self._process_data:
                await self.save_process_data("shutdown_save")
                
            self._is_initialized = False
            logger.info("Data manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during data manager shutdown")
            raise OperationError(f"Data manager shutdown failed: {str(e)}") from e

    async def set_user(self, username: str) -> None:
        """Set the current user for data collection."""
        try:
            self._current_user = username
            logger.debug(f"Current user set to: {username}")
            
            await self._message_broker.publish(
                "data/user/changed",
                {
                    "username": username,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting user: {e}")
            raise OperationError(f"Failed to set user: {str(e)}") from e

    async def set_cancelled(self, cancelled: bool = True) -> None:
        """Mark the current run as cancelled."""
        try:
            self._cancelled = cancelled
            logger.debug(f"Run marked as {'cancelled' if cancelled else 'not cancelled'}")
            
            await self._message_broker.publish(
                "data/run/status",
                {
                    "cancelled": cancelled,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting cancelled state: {e}")
            raise OperationError(f"Failed to set cancelled state: {str(e)}") from e

    def generate_filename(self, sequence_name: str) -> str:
        """Generate a filename for the process data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_prefix = self._current_user or "unknown_user"
        cancelled_suffix = "_cancelled" if self._cancelled else ""
        return f"{user_prefix}_{sequence_name}_{timestamp}{cancelled_suffix}.json"

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle incoming process data from tag updates."""
        try:
            for tag_name, value in data.items():
                if tag_name.startswith("process."):  # Only collect process-related tags
                    self._process_data[tag_name] = {
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            await self._message_broker.publish(
                "data/collection/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def save_process_data(self, sequence_name: str) -> None:
        """Save collected process data to file."""
        try:
            filename = self.generate_filename(sequence_name)
            filepath = self._data_path / filename
            
            # Add metadata to the process data
            metadata = {
                "user": self._current_user,
                "sequence": sequence_name,
                "timestamp": datetime.now().isoformat(),
                "cancelled": self._cancelled
            }
            
            data_to_save = {
                "metadata": metadata,
                "process_data": self._process_data
            }
            
            # Save data to file
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=2)
                
            logger.info(f"Process data saved to {filepath}")
            
            # Notify data saved
            await self._message_broker.publish(
                "data/saved",
                {
                    "filename": str(filepath),
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Clear collected data and reset cancelled flag after saving
            self._process_data.clear()
            self._cancelled = False
            
        except Exception as e:
            logger.error(f"Error saving process data: {e}")
            await self._message_broker.publish(
                "data/save/error",
                {
                    "error": str(e),
                    "sequence_name": sequence_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to save process data: {str(e)}") from e

    async def load_process_data(self, filepath: Path) -> Dict[str, Any]:
        """Load process data from file."""
        try:
            if not filepath.exists():
                raise FileNotFoundError(f"Process data file not found: {filepath}")
                
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            logger.info(f"Process data loaded from {filepath}")
            
            # Notify data loaded
            await self._message_broker.publish(
                "data/loaded",
                {
                    "filename": str(filepath),
                    "metadata": data.get("metadata", {}),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading process data: {e}")
            await self._message_broker.publish(
                "data/load/error",
                {
                    "error": str(e),
                    "filepath": str(filepath),
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to load process data: {str(e)}") from e

    def get_current_data(self) -> Dict[str, Any]:
        """Get current process data."""
        return self._process_data.copy()

    async def clear_data(self) -> None:
        """Clear collected process data."""
        try:
            self._process_data.clear()
            logger.debug("Process data cleared")
            
            await self._message_broker.publish(
                "data/cleared",
                {
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            raise OperationError(f"Failed to clear data: {str(e)}") from e