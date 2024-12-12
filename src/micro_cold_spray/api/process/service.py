"""Process API service."""

from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime

from ..base import ConfigurableService
from ..config import ConfigService
from ..communication import CommunicationService
from ..messaging import MessagingService
from ..validation import ValidationService
from ..data_collection import DataCollectionService
from .exceptions import ProcessError
from .services import (
    SequenceService,
    PatternService,
    ParameterService,
    ActionService
)


class ProcessService(ConfigurableService):
    """Service for managing the spray process."""

    def __init__(
        self,
        config_service: ConfigService,
        comm_service: CommunicationService,
        message_broker: MessagingService,
        data_collection_service: DataCollectionService,
        validation_service: ValidationService
    ):
        """Initialize process service.
        
        Args:
            config_service: Configuration service
            comm_service: Communication service for hardware control
            message_broker: Message broker service
            data_collection_service: Data collection service
            validation_service: Validation service
        """
        super().__init__(service_name="process")
        
        # Store service dependencies
        self._config_service = config_service
        self._comm_service = comm_service
        self._message_broker = message_broker
        self._data_collection = data_collection_service
        self._validation = validation_service
        
        # Initialize specialized services
        self._sequence_service = SequenceService(
            config_service,
            data_collection_service,
            validation_service
        )
        self._pattern_service = PatternService(config_service, message_broker)
        self._parameter_service = ParameterService(config_service)
        self._action_service = ActionService(config_service, comm_service, message_broker)
        
        # Process state
        self._config: Dict[str, Any] = {}
        self._current_sequence: Optional[Dict[str, Any]] = None

    async def _start(self) -> None:
        """Initialize process service."""
        try:
            # Load configuration
            config = await self._config_service.get_config("process")
            self._config = config.get("process", {})
            
            # Validate service dependencies
            if not await self._comm_service.check_connection():
                raise ProcessError("Communication service not connected")
                
            if not await self._data_collection.check_storage():
                raise ProcessError("Data collection storage not accessible")
            
            # Start specialized services
            await self._sequence_service.start()
            await self._pattern_service.start()
            await self._parameter_service.start()
            await self._action_service.start()
            
            logger.info("Process service started")
            
        except Exception as e:
            error_context = {"source": "process_service", "error": str(e)}
            logger.error("Failed to start process service", extra=error_context)
            raise ProcessError("Failed to start process service", error_context)

    async def _stop(self) -> None:
        """Stop process service."""
        try:
            # Stop current sequence if any
            if self._current_sequence:
                try:
                    await self.abort_sequence()
                except Exception as e:
                    logger.error(f"Error aborting sequence during shutdown: {e}")
            
            # Stop specialized services in reverse order
            services = [
                self._action_service,
                self._parameter_service,
                self._pattern_service,
                self._sequence_service
            ]
            
            for service in reversed(services):
                try:
                    await service.stop()
                except Exception as e:
                    logger.error(f"Error stopping {service.__class__.__name__}: {e}")
            
            logger.info("Process service stopped")
            
        except Exception as e:
            error_context = {"source": "process_service", "error": str(e)}
            logger.error("Failed to stop process service", extra=error_context)
            raise ProcessError("Failed to stop process service", error_context)

    async def start_sequence(self, sequence_id: str) -> None:
        """Start a spray sequence.
        
        Args:
            sequence_id: ID of sequence to start
            
        Raises:
            ProcessError: If sequence cannot be started
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        try:
            if self._current_sequence:
                raise ProcessError("Another sequence is already running")
                
            # Load and validate sequence
            sequence = await self._sequence_service.get_sequence(sequence_id)
            await self._validate_sequence(sequence)
            
            self._current_sequence = {
                "id": sequence_id,
                "sequence": sequence,
                "status": "running",
                "current_step": 0,
                "start_time": datetime.now().isoformat()
            }
            
            # Execute sequence steps
            await self._execute_sequence_steps()
            
            self._current_sequence["status"] = "completed"
            self._current_sequence["end_time"] = datetime.now().isoformat()
            
        except Exception as e:
            if self._current_sequence:
                self._current_sequence["status"] = "failed"
                self._current_sequence["error"] = str(e)
                self._current_sequence["end_time"] = datetime.now().isoformat()
                
            error_context = {
                "sequence_id": sequence_id,
                "error": str(e)
            }
            logger.error("Failed to execute sequence", extra=error_context)
            raise ProcessError("Failed to execute sequence", error_context)
        finally:
            # Always cleanup sequence state
            await self._cleanup_sequence()

    async def get_current_sequence(self) -> Optional[Dict[str, Any]]:
        """Get currently running sequence.
        
        Returns:
            Current sequence data or None if no sequence is running
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        return self._current_sequence

    async def abort_sequence(self) -> None:
        """Abort currently running sequence.
        
        Raises:
            ProcessError: If no sequence is running or abort fails
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        if not self._current_sequence:
            raise ProcessError("No sequence is currently running")
            
        try:
            # Abort current action if any
            await self._action_service.abort_current_action()
            
            self._current_sequence["status"] = "aborted"
            self._current_sequence["end_time"] = datetime.now().isoformat()
            
        except Exception as e:
            error_context = {
                "sequence": self._current_sequence,
                "error": str(e)
            }
            logger.error("Failed to abort sequence", extra=error_context)
            raise ProcessError("Failed to abort sequence", error_context)
        finally:
            # Always cleanup sequence state
            await self._cleanup_sequence()

    async def list_sequences(self) -> List[Dict[str, Any]]:
        """List available sequences.
        
        Returns:
            List of sequences with metadata
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        return await self._sequence_service.list_sequences()

    async def list_patterns(self) -> List[Dict[str, Any]]:
        """List available patterns.
        
        Returns:
            List of patterns with metadata
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        return await self._pattern_service.list_pattern_files()

    async def list_parameter_sets(self) -> List[Dict[str, Any]]:
        """List available parameter sets.
        
        Returns:
            List of parameter sets with metadata
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        return await self._parameter_service.list_parameter_sets()

    async def get_current_action(self) -> Optional[Dict[str, Any]]:
        """Get currently executing action.
        
        Returns:
            Current action data or None if no action is running
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        return await self._action_service.get_current_action()

    async def _validate_sequence(self, sequence: Dict[str, Any]) -> None:
        """Validate sequence configuration.
        
        Args:
            sequence: Sequence configuration to validate
            
        Raises:
            ProcessError: If sequence configuration is invalid
        """
        try:
            # Validate basic structure
            if not isinstance(sequence, dict):
                raise ProcessError("Invalid sequence format")
                
            # Validate pattern
            pattern_id = sequence.get("pattern")
            if not pattern_id:
                raise ProcessError("Sequence pattern not specified")
            await self._pattern_service.validate_pattern(pattern_id)
            
            # Validate parameters
            parameters = sequence.get("parameters", {})
            await self._parameter_service.validate_parameters(parameters)
            
            # Validate steps
            steps = sequence.get("steps", [])
            if not steps:
                raise ProcessError("Sequence has no steps")
                
            for step in steps:
                if not isinstance(step, dict):
                    raise ProcessError("Invalid step format")
                    
                action_type = step.get("action")
                if not action_type:
                    raise ProcessError("Step action not specified")
                    
                if action_type not in self._config.get("actions", {}).get("types", []):
                    raise ProcessError(f"Invalid action type: {action_type}")
                    
                # Validate step parameters
                step_params = step.get("parameters", {})
                if not isinstance(step_params, dict):
                    raise ProcessError("Invalid step parameters format")
                    
                # Validate step modifications
                modifications = step.get("modifications", {})
                if not isinstance(modifications, dict):
                    raise ProcessError("Invalid step modifications format")
                    
        except ProcessError:
            raise
        except Exception as e:
            raise ProcessError(f"Sequence validation failed: {e}")

    async def _execute_sequence_steps(self) -> None:
        """Execute sequence steps."""
        if not self._current_sequence:
            return
            
        sequence = self._current_sequence["sequence"]
        steps = sequence.get("steps", [])
        
        for i, step in enumerate(steps):
            if self._current_sequence["status"] != "running":
                break
                
            self._current_sequence["current_step"] = i
            
            try:
                action_type = step["action"]
                parameters = step.get("parameters", {})
                
                # Update parameters with sequence parameters
                parameters.update(sequence.get("parameters", {}))
                
                # Apply step modifications
                modifications = step.get("modifications", {})
                for param, value in modifications.items():
                    parameters[param] = value
                
                # Execute action
                await self._action_service.execute_action(action_type, parameters)
                
            except Exception as e:
                error_context = {
                    "step": i,
                    "action": step,
                    "error": str(e)
                }
                logger.error("Failed to execute sequence step", extra=error_context)
                raise ProcessError("Failed to execute sequence step", error_context)

    async def _cleanup_sequence(self) -> None:
        """Clean up sequence state."""
        try:
            # Stop data collection
            if self._data_collection.active_session:
                await self._data_collection.stop_collection()
                
            # Clear sequence state
            self._current_sequence = None
            
        except Exception as e:
            logger.error(f"Error cleaning up sequence state: {e}")
            # Don't re-raise, this is cleanup code
