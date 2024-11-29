"""Sequence management component."""
from typing import Dict, Any, Optional, List
from loguru import logger
import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
import yaml

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator
from ....components.operations.actions.action_manager import ActionManager
from ....exceptions import OperationError, SequenceError

class SequenceState(Enum):
    """Sequence execution states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class SequenceManager:
    """Manages spray sequence files and execution."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        sequence_path: Path = Path("data/sequences/library")
    ) -> None:
        """Initialize sequence manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._sequence_path = sequence_path
        self._loaded_sequence: Optional[Dict[str, Any]] = None
        self._active_step: Optional[int] = None

    async def initialize(self) -> None:
        """Initialize sequence manager."""
        try:
            # Create directories if they don't exist
            self._sequence_path.mkdir(parents=True, exist_ok=True)
            
            # Subscribe to sequence messages
            await self._message_broker.subscribe(
                "sequence/load",
                self._handle_load_request
            )
            await self._message_broker.subscribe(
                "sequence/save",
                self._handle_save_request
            )
            
            logger.info("Sequence manager initialized")
            
        except Exception as e:
            logger.exception("Failed to initialize sequence manager")
            raise SequenceError(f"Sequence manager initialization failed: {str(e)}") from e

    def get_available_sequences(self) -> List[Dict[str, Any]]:
        """Get list of available sequence files."""
        try:
            sequences = []
            for file in self._sequence_path.glob("**/*.yaml"):
                with open(file, 'r') as f:
                    seq = yaml.safe_load(f)
                    sequences.append({
                        "name": seq["sequence"]["metadata"]["name"],
                        "file": str(file.relative_to(self._sequence_path)),
                        "description": seq["sequence"]["metadata"]["description"]
                    })
            return sequences
            
        except Exception as e:
            logger.error(f"Error loading sequences: {e}")
            raise SequenceError(f"Failed to load sequences: {str(e)}") from e

    async def load_sequence(self, filename: str) -> Dict[str, Any]:
        """Load sequence file."""
        try:
            file_path = self._sequence_path / filename
            if not file_path.exists():
                raise SequenceError(f"Sequence file not found: {filename}")
                
            with open(file_path, 'r') as f:
                sequence = yaml.safe_load(f)
                
            self._loaded_sequence = sequence
            
            # Generate visualization data
            viz_data = self._generate_visualization_data(sequence)
            
            # Publish sequence loaded event
            await self._message_broker.publish(
                "sequence/loaded",
                {
                    "sequence": sequence,
                    "visualization": viz_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return sequence
            
        except Exception as e:
            logger.error(f"Error loading sequence: {e}")
            raise SequenceError(f"Failed to load sequence: {str(e)}") from e

    def _generate_visualization_data(self, sequence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate visualization data for sequence."""
        try:
            viz_data = []
            
            for step in sequence["sequence"]["steps"]:
                if "actions" in step:
                    for action in step["actions"]:
                        if "action_group" in action and action["action_group"] == "execute_pattern":
                            # Add pattern visualization data
                            pattern_data = {
                                "type": "pattern",
                                "origin": action["parameters"]["modifications"]["params"]["origin"],
                                "pattern_file": action["parameters"]["file"],
                                "passes": action["parameters"].get("passes", 1)
                            }
                            viz_data.append(pattern_data)
                        elif "action_group" in action and action["action_group"] == "move_to_trough":
                            # Add move visualization data
                            trough_pos = self._config_manager.get_config("hardware")["trough"]["position"]
                            move_data = {
                                "type": "move",
                                "x": trough_pos["x"],
                                "y": trough_pos["y"]
                            }
                            viz_data.append(move_data)
                            
            return viz_data
            
        except Exception as e:
            logger.error(f"Error generating visualization data: {e}")
            raise SequenceError(f"Failed to generate visualization: {str(e)}") from e

    async def save_sequence(
        self,
        sequence: Dict[str, Any],
        filename: Optional[str] = None
    ) -> None:
        """Save sequence file."""
        try:
            if filename is None:
                # Generate filename from metadata
                name = sequence["sequence"]["metadata"]["name"]
                filename = f"{name.lower().replace(' ', '_')}.yaml"
                
            file_path = self._sequence_path / filename
            
            with open(file_path, 'w') as f:
                yaml.safe_dump(sequence, f, sort_keys=False)
                
            logger.info(f"Saved sequence to {filename}")
            
            # Publish sequence saved event
            await self._message_broker.publish(
                "sequence/saved",
                {
                    "filename": filename,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error saving sequence: {e}")
            raise SequenceError(f"Failed to save sequence: {str(e)}") from e

    def _validate_sequence_patterns(self, sequence: Dict[str, Any]) -> None:
        """Validate all patterns in sequence stay within sprayable area."""
        try:
            hardware_config = self._config_manager.get_config("hardware")
            sprayable_area = hardware_config["substrate"]["sprayable"]
            
            for step in sequence["sequence"]["steps"]:
                if "actions" in step:
                    for action in step["actions"]:
                        if "action_group" in action and action["action_group"] == "execute_pattern":
                            # Get pattern origin
                            origin = action["parameters"]["modifications"]["params"]["origin"]
                            
                            # Load pattern file
                            pattern_file = action["parameters"]["file"]
                            pattern_type = pattern_file.split("_")[0]  # e.g., serpentine, spiral
                            
                            with open(self._pattern_path / pattern_type / pattern_file, 'r') as f:
                                pattern_data = yaml.safe_load(f)
                                
                            # Update pattern origin with sequence modification
                            pattern_data["pattern"]["params"]["origin"] = origin
                            
                            # Validate pattern bounds
                            self._pattern_manager._validate_sprayable_area(pattern_data)
                            
        except Exception as e:
            logger.error(f"Error validating sequence patterns: {e}")
            raise SequenceError(f"Failed to validate sequence patterns: {str(e)}") from e