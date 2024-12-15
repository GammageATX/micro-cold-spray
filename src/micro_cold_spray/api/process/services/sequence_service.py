"""Sequence management service."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import yaml
from loguru import logger

from ...base import BaseService
from ...config import ConfigService
from ...data_collection import DataCollectionService, DataCollectionError
from ...validation import ValidationService
from ..exceptions import ProcessError
from ..models import SequenceMetadata, SequenceStep


class SequenceService(BaseService):
    """Service for managing sequence operations."""

    def __init__(
        self,
        config_service: ConfigService,
        data_collection_service: DataCollectionService,
        validation_service: ValidationService
    ):
        """Initialize sequence service.
        
        Args:
            config_service: Configuration service
            data_collection_service: Data collection service
            validation_service: Validation service for domain rules
        """
        super().__init__(service_name="sequence", config_service=config_service)
        self._data_collection = data_collection_service
        self._validation = validation_service
        
        # Sequence state
        self._active_sequence: Optional[str] = None
        self._sequence_step: int = 0
        
        # Configuration
        self._data_path: Optional[Path] = None
        self._config: Dict[str, Any] = {}

    async def _start(self) -> None:
        """Initialize sequence service."""
        try:
            # Load configuration
            config = await self._config_service.get_config("process")
            self._config = config.get("process", {})
            
            # Load application config for paths
            app_config = await self._config_service.get_config("application")
            paths = app_config.get("application", {}).get("paths", {})
            
            # Set data paths
            root_path = Path(paths.get("data", {}).get("root", "data"))
            self._data_path = root_path
            
            logger.info("Sequence service started")
            
        except Exception as e:
            error_context = {
                "source": "sequence_service",
                "error": str(e)
            }
            logger.error("Failed to start sequence service", extra=error_context)
            raise ProcessError("Failed to start sequence service", error_context)

    async def start_sequence(self, sequence_id: str) -> None:
        """Start executing a sequence.
        
        Args:
            sequence_id: ID of sequence to execute
            
        Raises:
            ProcessError: If sequence cannot be started
        """
        try:
            if self._active_sequence:
                raise ProcessError("Sequence already running")
                
            # Validate sequence first
            await self.validate_sequence(sequence_id)
                
            # Start data collection
            try:
                collection_params = {
                    "sequence_id": sequence_id,
                    "data_path": str(self._data_path),
                    "config": self._config.get("data_collection", {})
                }
                await self._data_collection.start_collection(sequence_id, collection_params)
                
            except DataCollectionError as e:
                raise ProcessError(
                    "Failed to start data collection",
                    {"error": str(e), "context": e.context}
                )
                
            self._active_sequence = sequence_id
            self._sequence_step = 0
            
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
        """Cancel the current sequence.
        
        Raises:
            ProcessError: If sequence cannot be cancelled
        """
        try:
            if not self._active_sequence:
                return
                
            sequence_id = self._active_sequence
            
            # Stop data collection
            try:
                await self._data_collection.stop_collection()
            except DataCollectionError as e:
                logger.error(f"Error stopping data collection during cancel: {e}")
            
            self._active_sequence = None
            self._sequence_step = 0
            
            logger.info(f"Cancelled sequence: {sequence_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling sequence: {e}")
            raise ProcessError("Failed to cancel sequence", {"error": str(e)})

    async def create_sequence(self, sequence_data: Dict[str, Any]) -> str:
        """Create a new sequence file.
        
        Args:
            sequence_data: Sequence data to save
            
        Returns:
            Generated sequence ID
            
        Raises:
            ProcessError: If sequence creation fails
        """
        try:
            # Validate sequence structure
            await self._validate_sequence_structure(sequence_data)
            
            # Convert to models for validation
            metadata = sequence_data["sequence"]["metadata"]
            sequence_metadata = SequenceMetadata(
                name=metadata["name"],
                version=metadata["version"],
                created=datetime.fromisoformat(metadata["created"]),
                description=metadata.get("description")
            )
            
            steps = []
            for step_data in sequence_data["sequence"]["steps"]:
                step = SequenceStep(
                    action_group=step_data.get("action_group"),
                    pattern=step_data.get("pattern"),
                    parameters=step_data.get("parameters"),
                    modifications=step_data.get("modifications")
                )
                steps.append(step)
            
            # Validate against domain rules
            validation_result = await self._validation.validate_sequence(sequence_data)
            if not validation_result.get("valid", False):
                raise ProcessError(
                    "Sequence validation failed",
                    {"errors": validation_result.get("errors", [])}
                )
            
            # Generate unique sequence ID
            sequence_id = self._generate_sequence_id(sequence_metadata)
            
            # Save sequence file
            await self._save_sequence_file(sequence_id, sequence_data)
            
            logger.info(f"Created sequence: {sequence_id}")
            return sequence_id
            
        except Exception as e:
            error_context = {
                "error": str(e),
                "sequence_data": sequence_data
            }
            logger.error("Failed to create sequence", extra=error_context)
            raise ProcessError("Failed to create sequence", error_context)

    async def list_sequences(self) -> List[Dict[str, Any]]:
        """List available sequences.
        
        Returns:
            List of sequences with metadata
            
        Raises:
            ProcessError: If sequences cannot be listed
        """
        try:
            sequence_path = Path(self._config["paths"]["data"]["sequences"])
            sequences = []
            
            for file_path in sequence_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.load(f)
                        sequence = data.get("sequence", {})
                        metadata = sequence.get("metadata", {})
                        
                        # Convert to model for validation
                        sequence_metadata = SequenceMetadata(
                            name=metadata["name"],
                            version=metadata["version"],
                            created=datetime.fromisoformat(metadata["created"]),
                            description=metadata.get("description")
                        )
                        
                        sequences.append({
                            "id": file_path.stem,
                            "name": sequence_metadata.name,
                            "version": sequence_metadata.version,
                            "created": sequence_metadata.created.isoformat(),
                            "description": sequence_metadata.description,
                            "step_count": len(sequence.get("steps", []))
                        })
                except Exception as e:
                    logger.warning(f"Error loading sequence file {file_path}: {e}")
                    
            return sequences
            
        except Exception as e:
            raise ProcessError("Failed to list sequences", {"error": str(e)})

    @property
    def active_sequence(self) -> Optional[str]:
        """Get the currently active sequence ID."""
        return self._active_sequence

    @property
    def sequence_step(self) -> int:
        """Get the current sequence step."""
        return self._sequence_step

    async def _validate_sequence_structure(self, sequence_data: Dict[str, Any]) -> None:
        """Validate sequence file structure.
        
        This validates the basic structure and required fields,
        but not the domain-specific rules which are handled by
        the validation service.
        
        Args:
            sequence_data: Sequence data to validate
            
        Raises:
            ProcessError: If structure validation fails
        """
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

            # Validate steps have required fields
            for step in sequence["steps"]:
                if not any(key in step for key in ["pattern", "parameters", "action", "action_group"]):
                    raise ProcessError("Step missing valid action")
                
        except Exception as e:
            raise ProcessError("Sequence structure validation failed", {"error": str(e)})

    async def _save_sequence_file(self, sequence_id: str, sequence_data: Dict[str, Any]) -> None:
        """Save sequence file."""
        try:
            sequence_path = Path(self._config["paths"]["data"]["sequences"])
            file_path = sequence_path / f"{sequence_id}.yaml"
            
            # Ensure directory exists
            sequence_path.mkdir(parents=True, exist_ok=True)
            
            # Save file
            with open(file_path, 'w') as f:
                yaml.dump(sequence_data, f, sort_keys=False)
                
        except Exception as e:
            raise ProcessError(f"Failed to save sequence file: {e}")

    def _generate_sequence_id(self, metadata: SequenceMetadata) -> str:
        """Generate unique sequence ID from metadata.
        
        Args:
            metadata: Sequence metadata
            
        Returns:
            Generated sequence ID
            
        Raises:
            ProcessError: If ID generation fails
        """
        try:
            name = metadata.name.lower().replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{name}_{timestamp}"
            
        except Exception as e:
            raise ProcessError(f"Failed to generate sequence ID: {e}")

    async def get_sequence(self, sequence_id: str) -> Dict[str, Any]:
        """Get sequence by ID.
        
        Args:
            sequence_id: ID of sequence to get
            
        Returns:
            Sequence data
            
        Raises:
            ProcessError: If sequence not found
        """
        try:
            sequence_path = Path(self._config["paths"]["data"]["sequences"])
            file_path = sequence_path / f"{sequence_id}.yaml"
            
            if not file_path.exists():
                raise ProcessError(f"Sequence not found: {sequence_id}")
            
            with open(file_path) as f:
                data = yaml.load(f)
                
            # Validate sequence before returning
            await self._validate_sequence_structure(data)
            return data
            
        except Exception as e:
            raise ProcessError(f"Failed to get sequence: {e}")

    async def validate_sequence(self, sequence_id: str) -> None:
        """Validate an existing sequence.
        
        Args:
            sequence_id: ID of sequence to validate
            
        Raises:
            ProcessError: If sequence validation fails
        """
        try:
            # Load and validate structure
            sequence_data = await self.get_sequence(sequence_id)
            await self._validate_sequence_structure(sequence_data)
            
            # Validate against domain rules
            validation_result = await self._validation.validate_sequence(sequence_data)
            if not validation_result.get("valid", False):
                raise ProcessError(
                    "Sequence validation failed",
                    {"errors": validation_result.get("errors", [])}
                )
            
        except Exception as e:
            raise ProcessError(f"Sequence validation failed: {e}")
