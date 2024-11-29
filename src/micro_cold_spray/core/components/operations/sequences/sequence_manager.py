"""Sequence management component."""
from typing import Dict, Any, Optional, List
from loguru import logger
import asyncio
from datetime import datetime
from pathlib import Path
import yaml

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ....exceptions import SequenceError

class SequenceManager:
    """Manages sequence execution and control."""

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
        self._current_sequence: Optional[Dict[str, Any]] = None
        self._is_initialized = False
        self._is_running = False
        self._is_paused = False

    async def initialize(self) -> None:
        """Initialize sequence manager."""
        try:
            # Create directories if they don't exist
            self._sequence_path.mkdir(parents=True, exist_ok=True)

            # Subscribe to sequence messages
            await self._message_broker.subscribe(
                "sequence/load",
                self.handle_load_request
            )
            await self._message_broker.subscribe(
                "sequence/start",
                self.handle_start_request
            )
            await self._message_broker.subscribe(
                "sequence/stop",
                self.handle_stop_request
            )
            await self._message_broker.subscribe(
                "sequence/pause",
                self.handle_pause_request
            )
            await self._message_broker.subscribe(
                "sequence/resume",
                self.handle_resume_request
            )
            
            self._is_initialized = True
            logger.info("Sequence manager initialized")
            
        except Exception as e:
            logger.exception("Failed to initialize sequence manager")
            raise SequenceError(f"Sequence manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown sequence manager."""
        try:
            if self._is_running:
                await self.stop_sequence()
            self._is_initialized = False
            logger.info("Sequence manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during sequence manager shutdown")
            raise SequenceError(f"Sequence manager shutdown failed: {str(e)}") from e

    async def handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle sequence load request."""
        try:
            filename = data.get("filename")
            if not filename:
                raise SequenceError("No filename specified in load request")
                
            sequence = await self.load_sequence(filename)
            
            # Publish loaded sequence
            await self._message_broker.publish(
                "sequence/loaded",
                {
                    "sequence": sequence,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling load request: {e}")
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def handle_start_request(self, data: Dict[str, Any]) -> None:
        """Handle sequence start request."""
        try:
            if not self._current_sequence:
                raise SequenceError("No sequence loaded")
                
            await self.execute_sequence(self._current_sequence)
            
        except Exception as e:
            logger.error(f"Error handling start request: {e}")
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def handle_stop_request(self, _: Dict[str, Any]) -> None:
        """Handle sequence stop request."""
        try:
            await self.stop_sequence()
            
        except Exception as e:
            logger.error(f"Error handling stop request: {e}")
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def handle_pause_request(self, _: Dict[str, Any]) -> None:
        """Handle sequence pause request."""
        try:
            await self.pause_sequence()
            
        except Exception as e:
            logger.error(f"Error handling pause request: {e}")
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def handle_resume_request(self, _: Dict[str, Any]) -> None:
        """Handle sequence resume request."""
        try:
            await self.resume_sequence()
            
        except Exception as e:
            logger.error(f"Error handling resume request: {e}")
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def load_sequence(self, filename: str) -> Dict[str, Any]:
        """Load sequence from file."""
        try:
            file_path = self._sequence_path / filename
            with open(file_path, 'r') as f:
                sequence = yaml.safe_load(f)
                
            self._current_sequence = sequence
            
            # Publish loaded sequence
            await self._message_broker.publish(
                "sequence/loaded",
                {
                    "sequence": sequence,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return sequence
            
        except Exception as e:
            logger.error(f"Error loading sequence: {e}")
            raise SequenceError(f"Failed to load sequence: {str(e)}") from e

    async def execute_sequence(self, sequence: Dict[str, Any]) -> None:
        """Execute loaded sequence."""
        try:
            # Validate sequence first
            if "sequence" not in sequence or "steps" not in sequence["sequence"]:
                raise SequenceError("Invalid sequence format")
            
            self._is_running = True
            self._is_paused = False
            
            # Publish sequence started
            await self._message_broker.publish(
                "sequence/status",
                {
                    "state": "RUNNING",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Execute sequence steps
            for step in sequence["sequence"]["steps"]:
                if not self._is_running:
                    break
                    
                while self._is_paused:
                    await asyncio.sleep(0.1)
                    
                # Validate step format
                if "name" not in step:
                    raise SequenceError("Invalid step format - missing name")
                    
                # Validate step action exists
                action_config = self._config_manager.get_config("process")
                if (step["name"] not in action_config.get("atomic_actions", {}) and 
                    step["name"] not in action_config.get("action_groups", {})):
                    raise SequenceError(f"Invalid action: {step['name']}")
                    
                await self._execute_step(step)
                
            # Publish sequence completed
            if self._is_running:
                await self._message_broker.publish(
                    "sequence/complete",
                    {
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            self._is_running = False
            
        except Exception as e:
            logger.error(f"Error executing sequence: {e}")
            self._is_running = False
            
            # Publish error
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            raise SequenceError(f"Sequence execution failed: {str(e)}") from e

    async def pause_sequence(self) -> None:
        """Pause sequence execution."""
        try:
            if not self._is_running:
                raise SequenceError("No sequence running")
                
            self._is_paused = True
            
            await self._message_broker.publish(
                "sequence/status",
                {
                    "state": "PAUSED",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error pausing sequence: {e}")
            raise SequenceError(f"Failed to pause sequence: {str(e)}") from e

    async def resume_sequence(self) -> None:
        """Resume sequence execution."""
        try:
            if not self._is_running:
                raise SequenceError("No sequence running")
                
            self._is_paused = False
            
            await self._message_broker.publish(
                "sequence/status",
                {
                    "state": "RUNNING",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error resuming sequence: {e}")
            raise SequenceError(f"Failed to resume sequence: {str(e)}") from e

    async def stop_sequence(self) -> None:
        """Stop sequence execution."""
        try:
            self._is_running = False
            self._is_paused = False
            
            await self._message_broker.publish(
                "sequence/status",
                {
                    "state": "STOPPED",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error stopping sequence: {e}")
            raise SequenceError(f"Failed to stop sequence: {str(e)}") from e

    async def _execute_step(self, step: Dict[str, Any]) -> None:
        """Execute single sequence step."""
        try:
            # Publish step started
            await self._message_broker.publish(
                "sequence/step",
                {
                    "step": step["name"],
                    "state": "STARTED",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Execute step action
            await self._message_broker.publish(
                "action/execute",
                {
                    "type": step["name"],
                    "hardware_set": step["hardware_set"],
                    "pattern": step.get("pattern"),
                    "parameters": step["parameters"],
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Wait for action completion
            # TODO: Implement proper action completion handling
            await asyncio.sleep(1.0)
            
            # Publish step completed
            await self._message_broker.publish(
                "sequence/step",
                {
                    "step": step["name"],
                    "state": "COMPLETED",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing step {step['name']}: {e}")
            raise SequenceError(f"Step execution failed: {str(e)}") from e

    def _generate_visualization_data(self, sequence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate visualization data for sequence."""
        try:
            viz_data = []
            
            for step in sequence["sequence"]["steps"]:
                if pattern := step.get("pattern"):
                    viz_data.append({
                        "type": pattern["type"],
                        "pattern_file": pattern["file"],
                        "origin": pattern["parameters"].get("origin", [0, 0]),
                        "hardware_set": step["hardware_set"]
                    })
                    
            return viz_data
            
        except Exception as e:
            logger.error(f"Error generating visualization data: {e}")
            raise SequenceError(f"Visualization generation failed: {str(e)}") from e