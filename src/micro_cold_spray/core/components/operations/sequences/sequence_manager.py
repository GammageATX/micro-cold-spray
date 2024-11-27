"""Sequence management component."""
from typing import Dict, Any, Optional, List
from loguru import logger
import asyncio
from datetime import datetime
from enum import Enum

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator
from ....components.operations.actions.action_manager import ActionManager
from ....exceptions import OperationError

class SequenceState(Enum):
    """Sequence execution states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class SequenceManager:
    """Manages operation sequences and their execution."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        tag_manager: TagManager,
        message_broker: MessageBroker,
        process_validator: ProcessValidator,
        action_manager: ActionManager
    ):
        """Initialize with required dependencies."""
        self._config = config_manager
        self._tag_manager = tag_manager
        self._message_broker = message_broker
        self._validator = process_validator
        self._action_manager = action_manager
        
        self._current_sequence: Optional[Dict[str, Any]] = None
        self._current_step: int = 0
        self._execution_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("Sequence manager initialized")

    async def initialize(self) -> None:
        """Initialize sequence manager."""
        try:
            # Subscribe to sequence control messages
            await self._message_broker.subscribe("sequence/control", self._handle_sequence_control)
            logger.info("Sequence manager subscriptions initialized")
            
        except Exception as e:
            logger.exception("Failed to initialize sequence manager")
            raise OperationError(f"Sequence manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown sequence manager."""
        try:
            self._is_running = False
            
            if self._execution_task:
                self._execution_task.cancel()
                try:
                    await self._execution_task
                except asyncio.CancelledError:
                    pass
                    
            logger.info("Sequence manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during sequence manager shutdown")
            raise OperationError(f"Sequence manager shutdown failed: {str(e)}") from e

    async def _handle_sequence_control(self, data: Dict[str, Any]) -> None:
        """Handle sequence control messages."""
        try:
            command = data.get('command')
            if not command:
                raise ValueError("Missing command in sequence control message")
                
            if command == 'load':
                await self.load_sequence(data['sequence_name'])
            elif command == 'start':
                await self.start_sequence()
            elif command == 'pause':
                await self.pause_sequence()
            elif command == 'resume':
                await self.resume_sequence()
                
        except Exception as e:
            logger.error(f"Error handling sequence control: {e}")
            # Update error state through TagManager
            await self._tag_manager.set_tag(
                "sequence.error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            # Notify system through MessageBroker
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def load_sequence(self, sequence_name: str) -> None:
        """Load a sequence for execution."""
        try:
            if sequence_name not in self._sequences:
                raise ValueError(f"Sequence not found: {sequence_name}")
                
            # Validate sequence before loading
            await self._validator.validate_sequence(self._sequences[sequence_name])
            
            # Load sequence
            self._current_sequence = self._sequences[sequence_name]
            self._current_step = 0
            
            # Update state through TagManager
            await self._tag_manager.set_tag(
                "sequence.state",
                {
                    "name": sequence_name,
                    "state": SequenceState.IDLE.value,
                    "step_count": len(self._current_sequence['steps']),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify system through MessageBroker
            await self._message_broker.publish(
                "sequence/loaded",
                {
                    "sequence_name": sequence_name,
                    "step_count": len(self._current_sequence['steps'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error loading sequence {sequence_name}: {e}")
            raise

    async def start_sequence(self) -> None:
        """Start executing the loaded sequence."""
        try:
            if not self._current_sequence:
                raise ValueError("No sequence loaded")
                
            # Update state through TagManager
            await self._tag_manager.set_tag(
                "sequence.state",
                {
                    "state": SequenceState.RUNNING.value,
                    "step": self._current_step,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify start through MessageBroker
            await self._message_broker.publish(
                "sequence/started",
                {
                    "step": self._current_step
                }
            )
            
            # Execute sequence steps
            while self._current_step < len(self._current_sequence['steps']):
                step = self._current_sequence['steps'][self._current_step]
                
                # Update step through TagManager
                await self._tag_manager.set_tag(
                    "sequence.step",
                    {
                        "step": self._current_step,
                        "action": step['action'],
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Execute step action
                await self._action_manager.execute_action(
                    step['action'],
                    step['parameters']
                )
                
                self._current_step += 1
                
                # Update progress through TagManager
                await self._tag_manager.set_tag(
                    "sequence.progress",
                    {
                        "step": self._current_step,
                        "total_steps": len(self._current_sequence['steps']),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # Update completion state through TagManager
            await self._tag_manager.set_tag(
                "sequence.state",
                {
                    "state": SequenceState.COMPLETED.value,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify completion through MessageBroker
            await self._message_broker.publish(
                "sequence/completed",
                {}
            )
            
        except Exception as e:
            # Update error state through TagManager
            await self._tag_manager.set_tag(
                "sequence.state",
                {
                    "state": SequenceState.ERROR.value,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify error through MessageBroker
            await self._message_broker.publish(
                "sequence/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise

    def get_sequence(self, sequence_name: str) -> Dict[str, Any]:
        """Get a sequence definition."""
        if sequence_name not in self._sequences:
            raise ValueError(f"Sequence not found: {sequence_name}")
            
        return self._sequences[sequence_name].copy()

    def list_sequences(self) -> Dict[str, Dict[str, Any]]:
        """Get all sequence definitions."""
        return self._sequences.copy()

    def get_current_sequence(self) -> Optional[Dict[str, Any]]:
        """Get the currently loaded sequence."""
        return self._current_sequence.copy() if self._current_sequence else None

    def get_current_step(self) -> int:
        """Get the current step number."""
        return self._current_step