from typing import Dict, Any, Optional
import logging
import time
from pathlib import Path
import json

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class DataManager:
    """Manages process data collection and storage."""
    
    def __init__(self):
        """Initialize data manager."""
        self._config = ConfigManager()
        self._message_broker = MessageBroker()
        self._process_data: Dict[str, Dict[str, Any]] = {}
        self._data_path = Path("data/process")
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._current_user = None
        self._cancelled = False

        # Subscribe to tag updates for data collection
        self._message_broker.subscribe("tag_update", self._handle_tag_update)
        logger.info("Data manager initialized")

    def set_user(self, username: str):
        """Set the current user for data collection."""
        self._current_user = username
        logger.debug(f"Current user set to: {username}")

    def set_cancelled(self, cancelled: bool = True):
        """Mark the current run as cancelled."""
        self._cancelled = cancelled
        logger.debug(f"Run marked as {'cancelled' if cancelled else 'not cancelled'}")

    def generate_filename(self, sequence_name: str) -> str:
        """Generate a filename for the process data."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        user_prefix = self._current_user or "unknown_user"
        cancelled_suffix = "_cancelled" if self._cancelled else ""
        return f"{user_prefix}_{sequence_name}_{timestamp}{cancelled_suffix}.json"

    def _handle_tag_update(self, tag_data: Dict[str, Any]) -> None:
        """Handle incoming process data from tag updates."""
        for tag_name, value in tag_data.items():
            if tag_name.startswith("process."):  # Only collect process-related tags
                self._process_data[tag_name] = {
                    "value": value,
                    "timestamp": time.time()
                }

    def save_process_data(self, sequence_name: str) -> None:
        """Save collected process data to file."""
        try:
            filename = self.generate_filename(sequence_name)
            filepath = self._data_path / filename
            
            # Add metadata to the process data
            metadata = {
                "user": self._current_user,
                "sequence": sequence_name,
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cancelled": self._cancelled
            }
            
            data_to_save = {
                "metadata": metadata,
                "process_data": self._process_data
            }
            
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=2)
                
            logger.info(f"Process data saved to {filepath}")
            
            # Clear collected data and reset cancelled flag after saving
            self._process_data.clear()
            self._cancelled = False
            
        except Exception as e:
            logger.error(f"Error saving process data: {e}")
            raise

    def load_process_data(self, filepath: Path) -> Dict[str, Any]:
        """Load process data from file."""
        try:
            if not filepath.exists():
                raise FileNotFoundError(f"Process data file not found: {filepath}")
                
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            logger.info(f"Process data loaded from {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading process data: {e}")
            raise

    def get_current_data(self) -> Dict[str, Any]:
        """Get current process data."""
        return self._process_data.copy()

    def clear_data(self) -> None:
        """Clear collected process data."""
        self._process_data.clear()
        logger.debug("Process data cleared")