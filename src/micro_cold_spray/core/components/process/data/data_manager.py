"""Data Manager module."""
from datetime import datetime
from pathlib import Path
import yaml
from typing import Dict, Any, Optional

from loguru import logger

from micro_cold_spray.core.exceptions import CoreError, ValidationError
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager


class DataManager:
    """Manages process data collection and storage."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager):
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager

        # Data paths
        self._run_path = Path("data/runs")
        self._parameter_path = Path("data/parameters")
        self._nozzle_path = Path("data/parameters/nozzles")
        self._pattern_path = Path("data/patterns")
        self._sequence_path = Path("data/sequences")
        self._powder_path = Path("data/powders")

        # State tracking
        self._current_user: Optional[str] = None
        self._current_sequence: Optional[str] = None
        self._process_data: Dict[str, Any] = {}
        self._spray_active = False
        self._cancelled = False
        self._is_initialized = False

        logger.info("Data manager initialized")

    async def initialize(self) -> None:
        """Initialize data manager."""
        try:
            if self._is_initialized:
                return

            # Get data paths from application config
            app_config = await self._config_manager.get_config("application")
            data_paths = app_config.get("paths", {}).get("data", {})

            # Set up data directories
            self._run_path = Path(data_paths.get("runs", "data/runs"))
            self._parameter_path = Path(data_paths.get("parameters", "data/parameters"))
            self._nozzle_path = self._parameter_path / "nozzles"
            self._pattern_path = Path(data_paths.get("patterns", {}).get("root", "data/patterns"))
            self._sequence_path = Path(data_paths.get("sequences", "data/sequences"))
            self._powder_path = Path(data_paths.get("powders", "data/powders"))

            # Create directories if they don't exist
            for path in [
                self._run_path,
                self._parameter_path,
                self._nozzle_path,
                self._pattern_path / "custom",
                self._pattern_path / "serpentine",
                self._pattern_path / "spiral",
                self._sequence_path,
                self._powder_path
            ]:
                path.mkdir(parents=True, exist_ok=True)

            # Subscribe to message topics
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            await self._message_broker.subscribe("config/request/list_files", self._handle_list_files_request)

            self._is_initialized = True
            logger.info("Data manager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize data manager")
            raise CoreError("Data manager initialization failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_list_files_request(self, data: Dict[str, Any]) -> None:
        """Handle request to list available files."""
        try:
            file_type = data.get("type")
            if not file_type:
                raise ValidationError("No file type specified in request")

            # Map file type to directory
            type_mapping = {
                "parameters": self._parameter_path,
                "nozzles": self._nozzle_path,
                "patterns": {
                    "custom": self._pattern_path / "custom",
                    "serpentine": self._pattern_path / "serpentine",
                    "spiral": self._pattern_path / "spiral"
                },
                "sequences": self._sequence_path,
                "powders": self._powder_path
            }

            if file_type not in type_mapping:
                raise ValidationError(f"Invalid file type: {file_type}")

            files = []
            if isinstance(type_mapping[file_type], dict):
                # For patterns, list files from all subdirectories
                for subdir in type_mapping[file_type].values():
                    if subdir.exists():
                        for file_path in subdir.glob("*.yaml"):
                            # Include subdirectory in path
                            rel_path = file_path.relative_to(self._pattern_path)
                            files.append(str(rel_path.with_suffix("")))
            else:
                # For other types, list files directly
                base_path = type_mapping[file_type]
                if base_path.exists():
                    for file_path in base_path.glob("*.yaml"):
                        rel_path = file_path.relative_to(base_path)
                        files.append(str(rel_path.with_suffix("")))

            # Sort files for consistent ordering
            files.sort()

            # Add empty option for dropdowns
            files.insert(0, "")

            await self._message_broker.publish(
                "data/files/listed",
                {
                    "type": file_type,
                    "files": files
                }
            )
            logger.debug(f"Listed {len(files)} {file_type} files")
            return {"files": files}

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            await self._message_broker.publish(
                "data/files/error",
                {
                    "type": file_type,
                    "error": str(e)
                }
            )
            return {"files": []}

    async def _handle_nozzle_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save nozzle configuration to file."""
        try:
            name = data.get("name")
            nozzle_data = data.get("value")
            if not name or not nozzle_data:
                raise ValidationError("Missing name or nozzle data")

            # Get nozzle schema from file_format.yaml
            file_format = await self._config_manager.get_config("file_format")
            nozzle_schema = file_format.get("nozzles", {}).get("schema", {}).get("nozzle", {}).get("metadata", {})

            # Validate against schema
            if not self._validate_against_schema(nozzle_data.get("metadata", {}), nozzle_schema):
                raise ValidationError("Nozzle metadata does not match schema")

            # Save to file
            file_path = self._nozzle_path / f"{name}.yaml"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                yaml.safe_dump(nozzle_data, f, default_flow_style=False)

            logger.info(f"Nozzle configuration saved: {name}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Error saving nozzle configuration: {e}")
            return {"error": str(e)}

    async def _handle_nozzle_load(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Load nozzle configuration from file."""
        try:
            name = data.get("name")
            if not name:
                raise ValidationError("No nozzle name specified")

            file_path = self._nozzle_path / f"{name}.yaml"
            if not file_path.exists():
                raise FileNotFoundError(f"Nozzle not found: {name}")

            with open(file_path, "r") as f:
                nozzle_data = yaml.safe_load(f)

            return {"value": nozzle_data}

        except Exception as e:
            logger.error(f"Error loading nozzle configuration: {e}")
            return {"error": str(e)}

    async def _handle_nozzle_delete(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete nozzle configuration file."""
        try:
            name = data.get("name")
            if not name:
                raise ValidationError("No nozzle name specified")

            file_path = self._nozzle_path / f"{name}.yaml"
            if file_path.exists():
                file_path.unlink()
                return {"success": True}
            else:
                raise FileNotFoundError(f"Nozzle not found: {name}")

        except Exception as e:
            logger.error(f"Error deleting nozzle configuration: {e}")
            return {"error": str(e)}

    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate data against schema definition."""
        try:
            # Basic schema validation
            for field, field_schema in schema.items():
                if field_schema.get("required", False):
                    if field not in data:
                        logger.error(f"Missing required field: {field}")
                        return False
                    
                    value = data[field]
                    field_type = field_schema.get("type")
                    
                    # Type validation
                    if field_type == "string" and not isinstance(value, str):
                        logger.error(f"Field {field} must be string")
                        return False
                    
                    # Choice validation
                    choices = field_schema.get("choices", [])
                    if choices and value not in choices:
                        logger.error(f"Field {field} must be one of: {choices}")
                        return False

            return True

        except Exception as e:
            logger.error(f"Error during schema validation: {e}")
            return False

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates."""
        pass  # Implement if needed for process monitoring
