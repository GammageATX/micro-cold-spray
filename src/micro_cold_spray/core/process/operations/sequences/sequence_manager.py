"""Sequence management component."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import time
from loguru import logger
import yaml

from micro_cold_spray.core.exceptions import OperationError, ValidationError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.process.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.process.validation.process_validator import ProcessValidator


class SequenceManager:
    """Manages sequence loading and execution."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        action_manager: ActionManager,
        sequence_path: Path
    ):
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._action_manager = action_manager
        self._sequence_path = sequence_path
        self._process_validator = ProcessValidator(message_broker, config_manager)

        # File state
        self._current_sequence = None
        self._current_file = None
        self._is_modified = False

        # Runtime state
        self._is_running = False
        self._current_step_index = 0
        self._total_steps = 0
        self._sequence_start_time = None
        self._step_start_time = None

        logger.debug("Sequence manager initialized")

    async def initialize(self) -> None:
        """Initialize sequence manager."""
        try:
            # Subscribe to sequence request topic
            await self._message_broker.subscribe(
                "sequence/request",
                self._handle_sequence_request
            )

            # Publish initial state
            await self._publish_sequence_state("NONE")

            logger.info("Sequence manager initialization complete")

        except Exception as e:
            error_msg = f"Failed to initialize sequence manager: {str(e)}"
            logger.error(error_msg)
            await self._message_broker.publish("error", {
                "source": "sequence_manager",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            raise OperationError("sequence_manager", error_msg)

    async def _handle_sequence_request(self, data: Dict[str, Any]) -> None:
        """Handle sequence request messages."""
        request_id = data.get("request_id", "")
        try:
            request_type = data.get("request_type")
            if not request_type:
                raise ValidationError("Missing request type")

            if request_type == "load":
                filename = data.get("filename")
                if not filename:
                    raise ValidationError("Missing filename")
                await self._load_sequence(filename)
            elif request_type == "start":
                if self._is_running:
                    raise ValidationError("Sequence already running")
                await self.start_sequence()
            elif request_type == "stop":
                if not self._is_running:
                    raise ValidationError("No sequence running")
                await self.stop_sequence()
            elif request_type == "edit":
                if self._is_running:
                    raise ValidationError("Cannot edit sequence while running")
                await self._handle_edit_request(data)
            elif request_type == "save":
                if self._is_running:
                    raise ValidationError("Cannot save sequence while running")
                await self._handle_save_request(data)
            else:
                raise ValidationError(f"Invalid request type: {request_type}")

            # Send success response
            await self._message_broker.publish(
                "sequence/response",
                {
                    "request_id": request_id,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error handling sequence request: {error_msg}")

            # Send error response
            await self._message_broker.publish(
                "sequence/response",
                {
                    "request_id": request_id,
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Publish error event
            await self._message_broker.publish(
                "error",
                {
                    "source": "sequence_manager",
                    "error": error_msg,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _load_sequence(self, filename: str) -> None:
        """Load sequence from file."""
        try:
            if self._is_running:
                raise ValidationError("Cannot load sequence while running")

            file_path = self._sequence_path / filename
            if not file_path.exists():
                raise ValidationError(f"Sequence file not found: {filename}")

            # Load and validate sequence
            with open(file_path, 'r') as f:
                sequence = yaml.safe_load(f)

            if "sequence" not in sequence or "steps" not in sequence["sequence"]:
                raise ValidationError("Invalid sequence format")

            # Update internal state
            self._current_sequence = sequence
            self._current_file = file_path
            self._is_modified = False
            self._total_steps = len(sequence["sequence"]["steps"])

            # Update sequence state
            await self._publish_sequence_state("LOADED")

        except Exception as e:
            error_msg = f"Failed to load sequence: {str(e)}"
            logger.error(error_msg)
            raise OperationError("sequence_manager", error_msg)

    async def start_sequence(self) -> None:
        """Start sequence execution."""
        try:
            if not self._current_sequence:
                raise ValidationError("No sequence loaded")

            if self._is_running:
                raise ValidationError("Sequence already running")

            self._is_running = True
            self._current_step_index = 0
            self._sequence_start_time = time.time()

            await self._publish_sequence_state("RUNNING")
            await self._execute_sequence(self._current_sequence)

        except Exception as e:
            error_msg = f"Failed to start sequence: {str(e)}"
            logger.error(error_msg)
            self._is_running = False
            await self._publish_sequence_state("ERROR", str(e))
            raise OperationError("sequence_manager", error_msg)

    async def stop_sequence(self) -> None:
        """Stop sequence execution and mark as failed."""
        if self._is_running:
            self._is_running = False
            error_msg = "Sequence interrupted - experiment failed"
            logger.error(error_msg)
            await self._publish_sequence_state("ERROR", error_msg)
            raise OperationError("sequence_manager", error_msg)

    async def _execute_sequence(self, sequence: Dict[str, Any]) -> None:
        """Execute loaded sequence."""
        try:
            steps = sequence["sequence"]["steps"]
            self._total_steps = len(steps)

            for i, step in enumerate(steps):
                if not self._is_running:
                    # Sequence was stopped
                    raise OperationError("sequence_manager", "Sequence interrupted - experiment failed")

                self._current_step_index = i
                self._step_start_time = time.time()

                # Execute step and publish progress
                await self._execute_step(step)
                await self._publish_sequence_state("RUNNING")

            # Only mark as completed if we finished all steps
            if self._is_running:
                await self._publish_sequence_state("COMPLETED")
                self._is_running = False

        except Exception as e:
            logger.error(f"Error executing sequence: {e}")
            self._is_running = False
            await self._publish_sequence_state("ERROR", str(e))
            raise

    async def _publish_sequence_state(self, state: str, error: Optional[str] = None) -> None:
        """Publish sequence state update."""
        await self._message_broker.publish(
            "sequence/state",
            {
                "state": state,
                "file": str(self._current_file) if self._current_file else None,
                "sequence": self._current_sequence,
                "is_modified": self._is_modified,
                "current_step": self._current_step_index if self._is_running else None,
                "total_steps": self._total_steps,
                "progress": (self._current_step_index / self._total_steps * 100) if self._is_running and self._total_steps > 0 else None,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )

    async def _execute_step(self, step: Dict[str, Any]) -> None:
        """Execute a single sequence step."""
        try:
            # Validate step format
            if "action" not in step and "pattern" not in step and "parameters" not in step:
                raise ValidationError("Invalid step format - must contain action, pattern or parameters")

            # Execute the appropriate operation based on step type
            if "action" in step:
                await self._action_manager.execute_action(step["action"], step.get("parameters", {}))
            elif "pattern" in step:
                # Handle pattern execution
                pass
            elif "parameters" in step:
                # Handle parameter updates
                pass

            # Publish step completion
            await self._message_broker.publish(
                "sequence/step",
                {
                    "step": step,
                    "index": self._current_step_index,
                    "total": self._total_steps,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = f"Failed to execute step {self._current_step_index}: {str(e)}"
            logger.error(error_msg)
            raise OperationError("sequence_manager", error_msg)
