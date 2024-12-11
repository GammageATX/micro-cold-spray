"""Process management service."""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import yaml
import uuid

from ..base import BaseService
from ..config import ConfigService
from ..messaging import MessagingService
from ..data_collection import DataCollectionService, DataCollectionError

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
        config_service: ConfigService,
        message_broker: MessagingService,
        data_collection_service: DataCollectionService
    ):
        """Initialize process service.
        
        Args:
            config_service: Configuration service
            message_broker: Message broker service
            data_collection_service: Data collection service
        """
        super().__init__(service_name="process", config_service=config_service)
        self._message_broker = message_broker
        self._data_collection = data_collection_service
        
        # Process state
        self._active_sequence: Optional[str] = None
        self._sequence_step: int = 0
        self._process_lock = asyncio.Lock()
        
        # Configuration
        self._data_path: Optional[Path] = None
        self._config: Dict[str, Any] = {}
        self._action_groups: Dict[str, Dict[str, Any]] = {}
        
    async def _start(self) -> None:
        """Initialize process service."""
        try:
            # Load configuration
            config = await self._config_service.get_config("process")
            self._config = config.get("process", {})
            
            # Load action groups
            self._action_groups = self._config.get("action_groups", {})
            
            # Load application config for paths
            app_config = await self._config_service.get_config("application")
            paths = app_config.get("application", {}).get("paths", {})
            
            # Set data paths
            root_path = Path(paths.get("data", {}).get("root", "data"))
            self._data_path = root_path
            
            # Subscribe to state changes
            await self._message_broker.subscribe(
                "state/changed",
                self._handle_state_change
            )
            
            logger.info("Process service started")
            
        except Exception as e:
            error_context = {
                "source": "process_service",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error("Failed to start process service", extra=error_context)
            raise ProcessError("Failed to start process service", error_context)

    async def define_action_group(self, group_data: Dict[str, Any]) -> None:
        """Define a new action group.
        
        Args:
            group_data: Action group definition containing:
                - name: Group name
                - actions: List of actions
                - parameters: Optional parameters
                
        Raises:
            ProcessError: If action group cannot be defined
        """
        try:
            # Validate group data
            if "name" not in group_data:
                raise ProcessError("Missing action group name")
            if "actions" not in group_data:
                raise ProcessError("Missing action group actions")
                
            # Register group
            group_name = group_data["name"]
            self._action_groups[group_name] = {
                "actions": group_data["actions"],
                "parameters": group_data.get("parameters", {})
            }
            
            logger.info(f"Defined action group: {group_name}")
            
        except Exception as e:
            error_context = {
                "group_data": group_data,
                "error": str(e)
            }
            logger.error("Failed to define action group", extra=error_context)
            raise ProcessError("Failed to define action group", error_context)

    async def execute_action_group(self, group_name: str, parameters: Dict[str, Any]) -> None:
        """Execute an action group.
        
        Args:
            group_name: Name of action group to execute
            parameters: Parameters for action group
            
        Raises:
            ProcessError: If action group cannot be executed
        """
        try:
            # Validate group exists
            if group_name not in self._action_groups:
                raise ProcessError(f"Action group not found: {group_name}")
                
            group = self._action_groups[group_name]
            
            # Execute each action in group
            for action in group["actions"]:
                action_name = action["name"]
                action_params = {**group["parameters"], **parameters, **action.get("parameters", {})}
                
                await self._execute_action(action_name, action_params)
                
                # Handle delays between actions
                if "delay" in action:
                    await asyncio.sleep(action["delay"])
                    
            logger.info(f"Executed action group: {group_name}")
            
        except Exception as e:
            error_context = {
                "group_name": group_name,
                "parameters": parameters,
                "error": str(e)
            }
            logger.error("Failed to execute action group", extra=error_context)
            raise ProcessError("Failed to execute action group", error_context)

    async def _execute_step(self, step: Dict[str, Any]) -> None:
        """Execute a sequence step.
        
        Args:
            step: Step data to execute
            
        Raises:
            ProcessError: If step execution fails
        """
        try:
            # Execute pattern if present
            if "pattern" in step:
                await self._execute_pattern(step["pattern"], step.get("parameters", {}))
                
            # Apply parameters if present
            if "parameters" in step:
                await self._apply_parameters(step["parameters"])
                
            # Execute action if present
            if "action" in step:
                await self._execute_action(step["action"], step.get("parameters", {}))
                
            # Execute action group if present
            if "action_group" in step:
                await self.execute_action_group(step["action_group"], step.get("parameters", {}))
                
            # Log step completion
            await self._message_broker.publish(
                "sequence/step",
                {
                    "sequence_id": self._active_sequence,
                    "step": self._sequence_step,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Move to next step
            self._sequence_step += 1
            
        except Exception as e:
            error_context = {
                "step": step,
                "error": str(e)
            }
            logger.error("Step execution failed", extra=error_context)
            raise ProcessError("Step execution failed", error_context)

    async def _validate_step(self, step: Dict[str, Any]) -> None:
        """Validate a sequence step.
        
        Args:
            step: Step data to validate
            
        Raises:
            ProcessError: If step validation fails
        """
        try:
            # Check step has valid action
            if not any(key in step for key in ["pattern", "parameters", "action", "action_group"]):
                raise ProcessError("Step missing valid action")
                
            # Validate pattern if present
            if "pattern" in step:
                await self._validate_pattern_exists(step["pattern"])
                
            # Validate parameters if present
            if "parameters" in step:
                await self._validate_parameters_exist(step["parameters"])
                
            # Validate action group if present
            if "action_group" in step:
                if step["action_group"] not in self._action_groups:
                    raise ProcessError(f"Action group not found: {step['action_group']}")
                
        except Exception as e:
            error_context = {
                "step": step,
                "error": str(e)
            }
            logger.error("Step validation failed", extra=error_context)
            raise ProcessError("Step validation failed", error_context)

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

    async def _execute_step(self, step: Dict[str, Any]) -> None:
        """Execute a sequence step."""
        try:
            if "pattern" in step:
                # Execute pattern step
                await self._pattern_manager.execute_pattern(
                    step["pattern"],
                    step.get("parameters", {})
                )
                await self._log_process_data({
                    "type": "pattern",
                    "pattern": step["pattern"],
                    "parameters": step.get("parameters", {})
                })

    async def create_sequence(self, sequence_data: Dict[str, Any]) -> str:
        """Create a new sequence file."""
        try:
            # Validate sequence structure
            await self._validate_sequence_structure(sequence_data)
            
            # Generate unique sequence ID
            sequence_id = self._generate_sequence_id(sequence_data)
            
            # Save sequence file
            await self._save_sequence_file(sequence_id, sequence_data)
            
            return sequence_id
            
        except Exception as e:
            raise ProcessError("Failed to create sequence", {"error": str(e)})

    async def create_parameter_set(self, parameter_data: Dict[str, Any]) -> str:
        """Create a new parameter set file."""
        try:
            # Generate parameter set ID
            param_id = self._generate_parameter_id(parameter_data)
            
            # Save parameter file
            await self._save_parameter_file(param_id, parameter_data)
            
            return param_id
            
        except Exception as e:
            raise ProcessError("Failed to create parameter set", {"error": str(e)})

    @property
    def active_sequence(self) -> Optional[str]:
        """Get the currently active sequence ID."""
        return self._active_sequence

    @property
    def sequence_step(self) -> int:
        """Get the current sequence step."""
        return self._sequence_step

    async def _validate_sequence_execution(self, sequence_id: str) -> None:
        """Validate sequence before execution."""
        try:
            # Load sequence
            sequence = await self._load_sequence(sequence_id)
            
            # Validate all components
            await self._validate_sequence_patterns(sequence)
            await self._validate_sequence_parameters(sequence)
            await self._validate_sequence_actions(sequence)
            
            # Validate hardware requirements
            await self._validate_hardware_requirements(sequence)
            
            # Check safety constraints
            await self._safety_monitor.validate_sequence(sequence)
            
        except Exception as e:
            raise ProcessError("Sequence validation failed", {"error": str(e)})

    async def _validate_with_validation_api(
        self, 
        validation_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Send validation request to Validation API."""
        try:
            response = await self._validation_client.validate(validation_type, data)
            if not response["valid"]:
                raise ProcessError(
                    "Validation failed",
                    {"errors": response["errors"]}
                )
        except Exception as e:
            raise ProcessError("Validation request failed", {"error": str(e)})

    async def _validate_sequence_structure(self, sequence_data: Dict[str, Any]) -> None:
        """Validate sequence file structure and references."""
        try:
            # Validate basic structure
            if "sequence" not in sequence_data:
                raise ProcessError("Missing sequence root element")
            
            sequence = sequence_data["sequence"]
            if "metadata" not in sequence or "steps" not in sequence:
                raise ProcessError("Sequence missing required sections")

            # Validate metadata
            required_metadata = ["name", "version", "created"]
            for field in required_metadata:
                if field not in sequence["metadata"]:
                    raise ProcessError(f"Missing required metadata: {field}")

            # Validate steps
            for step in sequence["steps"]:
                # Validate action groups
                if "action_group" in step:
                    await self._validate_action_group_exists(step["action_group"])
                    
                # Validate pattern references
                if "actions" in step:
                    for action in step["actions"]:
                        if action.get("action_group") == "execute_pattern":
                            pattern_file = action.get("parameters", {}).get("file")
                            if pattern_file:
                                await self._validate_pattern_file_exists(pattern_file)
                                
                        elif action.get("action_group") == "apply_parameters":
                            param_file = action.get("parameters", {}).get("file")
                            if param_file:
                                await self._validate_parameter_file_exists(param_file)

        except Exception as e:
            raise ProcessError("Sequence validation failed", {"error": str(e)})

    async def _validate_parameter_file_exists(self, filename: str) -> None:
        """Verify parameter file exists."""
        param_path = Path("data/parameters") / filename
        if not param_path.exists():
            raise ProcessError(f"Parameter file not found: {filename}")

    async def _validate_pattern_file_exists(self, filename: str) -> None:
        """Verify pattern file exists."""
        pattern_path = Path("data/patterns") / filename
        if not pattern_path.exists():
            raise ProcessError(f"Pattern file not found: {filename}")

    async def _validate_action_group_exists(self, group_name: str) -> None:
        """Verify action group is defined."""
        if not await self._action_manager.group_exists(group_name):
            raise ProcessError(f"Action group not found: {group_name}")

    async def list_parameter_files(self) -> List[Dict[str, Any]]:
        """List available parameter files with metadata."""
        try:
            param_path = Path(self._config["paths"]["data"]["parameters"])
            files = []
            
            for file_path in param_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.safe_load(f)
                        files.append({
                            "name": file_path.stem,
                            "path": str(file_path),
                            "metadata": data.get("metadata", {})
                        })
                except Exception as e:
                    logger.warning(f"Error loading parameter file {file_path}: {e}")
                    
            return files
            
        except Exception as e:
            raise ProcessError("Failed to list parameter files", {"error": str(e)})

    async def list_pattern_files(self) -> List[Dict[str, Any]]:
        """List available pattern files with metadata."""
        try:
            pattern_path = Path(self._config["paths"]["data"]["patterns"]["root"])
            files = []
            
            for file_path in pattern_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.safe_load(f)
                        files.append({
                            "name": file_path.stem,
                            "path": str(file_path),
                            "type": data.get("type"),
                            "metadata": data.get("metadata", {})
                        })
                except Exception as e:
                    logger.warning(f"Error loading pattern file {file_path}: {e}")
                    
            return files
            
        except Exception as e:
            raise ProcessError("Failed to list pattern files", {"error": str(e)})

    async def list_sequence_files(self) -> List[Dict[str, Any]]:
        """List available sequence files with metadata."""
        try:
            sequence_path = Path(self._config["paths"]["data"]["sequences"])
            files = []
            
            for file_path in sequence_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.safe_load(f)
                        sequence = data.get("sequence", {})
                        files.append({
                            "name": file_path.stem,
                            "path": str(file_path),
                            "metadata": sequence.get("metadata", {}),
                            "step_count": len(sequence.get("steps", []))
                        })
                except Exception as e:
                    logger.warning(f"Error loading sequence file {file_path}: {e}")
                    
            return files
            
        except Exception as e:
            raise ProcessError("Failed to list sequence files", {"error": str(e)})

    async def _save_sequence_file(self, sequence_id: str, sequence_data: Dict[str, Any]) -> None:
        """Save sequence file."""
        try:
            sequence_path = Path(self._config["paths"]["data"]["sequences"])
            file_path = sequence_path / f"{sequence_id}.yaml"
            
            # Ensure directory exists
            sequence_path.mkdir(parents=True, exist_ok=True)
            
            # Save file
            with open(file_path, 'w') as f:
                yaml.safe_dump(sequence_data, f, sort_keys=False)
                
        except Exception as e:
            raise ProcessError(f"Failed to save sequence file: {e}")

    async def _generate_sequence_id(self, sequence_data: Dict[str, Any]) -> str:
        """Generate unique sequence ID from metadata."""
        try:
            metadata = sequence_data["sequence"]["metadata"]
            name = metadata["name"].lower().replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{name}_{timestamp}"
            
        except Exception as e:
            raise ProcessError(f"Failed to generate sequence ID: {e}")

    async def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> None:
        """Execute atomic action via Communication API."""
        await self._message_broker.publish(
            "action/request",
            {
                "action": action_name,
                "parameters": parameters
            }
        )

    async def validate_pattern(self, pattern_data: Dict[str, Any]) -> None:
        """Validate pattern via Validation API."""
        await self._message_broker.publish(
            "validation/request",
            {
                "type": "pattern",
                "data": pattern_data
            }
        )

    async def register_action_group(self, group_name: str, actions: List[Dict[str, Any]]) -> None:
        """Register new action group."""
        await self._action_manager.register_group(group_name, actions)

    async def apply_parameters(self, parameter_set: str) -> None:
        """Apply parameter set to hardware."""
        await self._parameter_manager.apply_parameters(parameter_set)

    async def get_current_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        return await self._parameter_manager.get_current_parameters()

    async def generate_pattern(self, pattern_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate new pattern."""
        return await self._pattern_manager.generate_pattern(pattern_type, parameters)

    async def execute_pattern(self, pattern_id: str, modifications: Dict[str, Any] = None) -> None:
        """Execute pattern with optional modifications."""
        await self._pattern_manager.execute_pattern(pattern_id, modifications)

    async def execute_sequence_step(self, step: Dict[str, Any]) -> None:
        """Execute single sequence step."""
        try:
            # Handle different step types
            if "action_group" in step:
                await self.execute_action_group(step["action_group"], step.get("parameters", {}))
            elif "pattern" in step:
                await self.execute_pattern(step["pattern"], step.get("modifications", {}))
            elif "parameters" in step:
                await self.apply_parameters(step["parameters"])
            
            # Log step completion
            await self._log_process_data({
                "type": "step_complete",
                "step": step,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            raise ProcessError(f"Step execution failed: {e}")

    async def _execute_atomic_action(self, action: str, params: Dict[str, Any]) -> None:
        """Execute atomic action via Communication API."""
        try:
            await self._message_broker.publish(
                "action/request",
                {
                    "action": action,
                    "parameters": params,
                    "request_id": str(uuid.uuid4())
                }
            )
            # Wait for completion/validation
            # Handle response
        except Exception as e:
            raise ProcessError(f"Action execution failed: {action}", {"error": str(e)})

    async def _execute_action_group(self, group: str, params: Dict[str, Any]) -> None:
        """Execute predefined action group."""
        try:
            # Get group definition from config
            group_def = self._config["process"]["action_groups"][group]
            
            # Execute each step
            for step in group_def["steps"]:
                if "action" in step:
                    await self._execute_atomic_action(
                        step["action"],
                        self._resolve_parameters(step, params)
                    )
                elif "validation" in step:
                    await self._validate_condition(step["validation"])
                elif "time_delay" in step:
                    await asyncio.sleep(step["time_delay"])
                    
        except Exception as e:
            raise ProcessError(f"Action group failed: {group}", {"error": str(e)})

class SafetyMonitor:
    async def check_pattern_safety(self, pattern: Dict[str, Any]) -> None:
        """Verify pattern safety constraints."""
        # Check motion limits
        # Verify speed constraints
        # Check collision avoidance
        # Validate work envelope
