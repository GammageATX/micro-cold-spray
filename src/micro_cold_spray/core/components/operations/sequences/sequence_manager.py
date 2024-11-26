"""Sequence management component."""
from typing import Dict, Any, Optional, List
import logging
import time
from enum import Enum

from ....infrastructure.messaging.message_broker import MessageBroker, Message, MessageType
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator
from ....components.operations.actions.action_manager import ActionManager

logger = logging.getLogger(__name__)

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
        process_validator: ProcessValidator,
        action_manager: ActionManager
    ):
        self._config = config_manager
        self._tag_manager = tag_manager
        self._validator = process_validator
        self._action_manager = action_manager
        self._message_broker = MessageBroker()
        
        self._current_sequence: Optional[Dict[str, Any]] = None
        self._current_step: int = 0
        
        # Only subscribe to sequence control messages
        self._message_broker.subscribe("sequence_control", self._handle_sequence_control)
        
        logger.info("Sequence manager initialized")

    async def _handle_sequence_control(self, message: Message) -> None:
        """Handle sequence control messages."""
        try:
            command = message.get('command')
            if command == 'load':
                await self.load_sequence(message.data['sequence_name'])
            elif command == 'start':
                await self.start_sequence()
            elif command == 'pause':
                await self.pause_sequence()
            elif command == 'resume':
                await self.resume_sequence()
        except Exception as e:
            logger.error(f"Error handling sequence control: {e}")
            # Update error state through TagManager
            self._tag_manager.set_tag(
                "sequence.error",
                {
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
            # Notify system through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="sequence/error",
                    type=MessageType.ERROR,
                    data={"error": str(e)}
                )
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
            self._tag_manager.set_tag(
                "sequence.state",
                {
                    "name": sequence_name,
                    "state": SequenceState.IDLE.value,
                    "step_count": len(self._current_sequence['steps']),
                    "timestamp": time.time()
                }
            )
            
            # Notify system through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="sequence/loaded",
                    type=MessageType.SEQUENCE_STATUS,
                    data={
                        "sequence_name": sequence_name,
                        "step_count": len(self._current_sequence['steps'])
                    }
                )
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
            self._tag_manager.set_tag(
                "sequence.state",
                {
                    "state": SequenceState.RUNNING.value,
                    "step": self._current_step,
                    "timestamp": time.time()
                }
            )
            
            # Notify start through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="sequence/started",
                    type=MessageType.SEQUENCE_STATUS,
                    data={"step": self._current_step}
                )
            )
            
            # Execute sequence steps
            while self._current_step < len(self._current_sequence['steps']):
                step = self._current_sequence['steps'][self._current_step]
                
                # Update step through TagManager
                self._tag_manager.set_tag(
                    "sequence.step",
                    {
                        "step": self._current_step,
                        "action": step['action'],
                        "timestamp": time.time()
                    }
                )
                
                # Execute step action
                await self._action_manager.execute_action(
                    step['action'],
                    step['parameters']
                )
                
                self._current_step += 1
                
                # Update progress through TagManager
                self._tag_manager.set_tag(
                    "sequence.progress",
                    {
                        "step": self._current_step,
                        "total_steps": len(self._current_sequence['steps']),
                        "timestamp": time.time()
                    }
                )
            
            # Update completion state through TagManager
            self._tag_manager.set_tag(
                "sequence.state",
                {
                    "state": SequenceState.COMPLETED.value,
                    "timestamp": time.time()
                }
            )
            
            # Notify completion through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="sequence/completed",
                    type=MessageType.SEQUENCE_STATUS,
                    data={}
                )
            )
            
        except Exception as e:
            # Update error state through TagManager
            self._tag_manager.set_tag(
                "sequence.state",
                {
                    "state": SequenceState.ERROR.value,
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
            
            # Notify error through MessageBroker
            self._message_broker.publish(
                Message(
                    topic="sequence/error",
                    type=MessageType.ERROR,
                    data={"error": str(e)}
                )
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