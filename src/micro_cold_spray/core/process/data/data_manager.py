"""Data Manager module."""
from datetime import datetime
from pathlib import Path
import yaml
from typing import Dict, Any, Optional, List
import copy

from loguru import logger

from micro_cold_spray.core.exceptions import CoreError, ValidationError
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager


class DataManager:
    """Data management component."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager,
            data_root: Optional[Path] = None) -> None:
        """Initialize data manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._data_root = data_root or Path("data")
        self._is_initialized = False
        self._file_format = None

    async def initialize(self) -> None:
        """Initialize data manager."""
        try:
            if self._is_initialized:
                return

            # Get data paths from application config
            app_config = await self._config_manager.get_config("application")
            data_paths = app_config.get("paths", {}).get("data", {})

            # Set up data directories from config with fallbacks
            self._run_path = Path(data_paths.get("runs", "data/runs"))
            self._parameter_path = Path(data_paths.get("parameters", "data/parameters"))
            self._nozzle_path = Path(data_paths.get("nozzles", "data/parameters/nozzles"))
            self._pattern_path = Path(data_paths.get("patterns", {}).get("root", "data/patterns"))
            self._sequence_path = Path(data_paths.get("sequences", "data/sequences"))
            self._powder_path = Path(data_paths.get("powders", "data/powders"))

            # Create directories
            for path in [
                self._run_path,
                self._parameter_path,
                self._nozzle_path,
                self._pattern_path,
                self._sequence_path,
                self._powder_path
            ]:
                path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {path}")

            # Create pattern subdirectories from config
            pattern_paths = data_paths.get("patterns", {})
            if isinstance(pattern_paths, dict):
                for subdir in ["custom", "serpentine", "spiral"]:
                    if subdir in pattern_paths:
                        path = Path(pattern_paths[subdir])
                        path.mkdir(parents=True, exist_ok=True)
                        logger.debug(f"Created pattern directory: {path}")

            # Load file format specification
            self._file_format = await self._config_manager.get_config("file_format")

            # Update nozzle choices in file format schema
            await self._update_nozzle_choices()

            # Subscribe to message topics
            await self._message_broker.subscribe("data/request", self._handle_data_request)

            self._is_initialized = True
            logger.info("Data manager initialization complete")
            logger.debug(f"Using sequence path: {self._sequence_path}")

        except Exception as e:
            logger.exception("Failed to initialize data manager")
            raise CoreError("Data manager initialization failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _update_nozzle_choices(self) -> None:
        """Update nozzle choices in file format schema."""
        try:
            nozzle_names = []
            if self._nozzle_path.exists():
                for file_path in self._nozzle_path.glob("*.yaml"):
                    with open(file_path, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and "nozzle" in data and "name" in data["nozzle"]:
                            nozzle_names.append(data["nozzle"]["name"])

            nozzle_names.sort()
            logger.debug(f"Found {len(nozzle_names)} nozzle choices")

            # Update choices in file format schema
            if self._file_format and "parameters" in self._file_format:
                params = self._file_format["parameters"]
                if "nozzle" in params and "type" in params["nozzle"]:
                    params["nozzle"]["type"]["choices"] = nozzle_names

        except Exception as e:
            logger.error(f"Error updating nozzle choices: {e}")
            # Don't raise - just log the error since this is non-critical

    async def generate_file(
            self,
            file_type: str,
            name: str,
            template_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a new file from template with proper structure."""
        try:
            if not self._file_format:
                raise ValidationError("File format not loaded")

            # Get format specification for file type
            format_spec = self._file_format.get("file_format", {}).get(file_type)
            if not format_spec:
                raise ValidationError(f"Unknown file type: {file_type}")

            # Start with empty template
            file_data = {}

            # Add metadata
            if "metadata" in format_spec:
                metadata = {}
                for field, field_spec in format_spec["metadata"].items():
                    if field_spec.get("type") == "string" and field_spec.get("default", "").startswith("%"):
                        # Format date/time fields
                        metadata[field] = datetime.now().strftime(field_spec["default"])
                    else:
                        metadata[field] = field_spec.get("default")
                metadata["name"] = name
                file_data["metadata"] = metadata

            # Add template data if provided
            if template_data:
                self._merge_template_data(file_data, template_data, format_spec)

            # Validate generated file
            await self.validate_file(file_type, file_data)

            return file_data

        except Exception as e:
            logger.error(f"Error generating file: {e}")
            raise ValidationError(f"File generation failed: {str(e)}")

    async def validate_file(
            self,
            file_type: str,
            file_data: Dict[str, Any]) -> None:
        """Validate file against format specification."""
        try:
            if not self._file_format:
                raise ValidationError("File format not loaded")

            format_spec = self._file_format.get("file_format", {}).get(file_type)
            if not format_spec:
                raise ValidationError(f"Unknown file type: {file_type}")

            # Validate structure recursively
            self._validate_structure(file_data, format_spec, [])

        except Exception as e:
            logger.error(f"File validation error: {e}")
            raise ValidationError(f"File validation failed: {str(e)}")

    def _validate_structure(
            self,
            data: Dict[str, Any],
            spec: Dict[str, Any],
            path: List[str]) -> None:
        """Recursively validate data structure against specification."""
        current_path = ".".join(path) if path else "root"

        # Check required sections
        for section, section_spec in spec.items():
            if section not in data and not section_spec.get("optional", False):
                raise ValidationError(f"Missing required section: {current_path}.{section}")

        # Validate each field
        for field, value in data.items():
            if field not in spec:
                raise ValidationError(f"Unknown field: {current_path}.{field}")

            field_spec = spec[field]
            field_path = path + [field]

            # Handle different field types
            field_type = field_spec.get("type")
            if field_type == "string":
                if not isinstance(value, str):
                    raise ValidationError(f"Field {current_path}.{field} must be string")
            elif field_type == "number":
                if not isinstance(value, (int, float)):
                    raise ValidationError(f"Field {current_path}.{field} must be number")
                # Check range if specified
                if "min" in field_spec and value < field_spec["min"]:
                    raise ValidationError(
                        f"Field {current_path}.{field} below minimum: {value} < {field_spec['min']}")
                if "max" in field_spec and value > field_spec["max"]:
                    raise ValidationError(
                        f"Field {current_path}.{field} above maximum: {value} > {field_spec['max']}")
            elif field_type == "choice":
                if value not in field_spec.get("choices", []):
                    raise ValidationError(
                        f"Invalid choice for {current_path}.{field}: {value}")
            elif field_type == "list":
                if not isinstance(value, list):
                    raise ValidationError(f"Field {current_path}.{field} must be list")
                # Validate list items if item spec provided
                if "items" in field_spec:
                    for i, item in enumerate(value):
                        self._validate_structure(
                            {"item": item},
                            {"item": field_spec["items"]},
                            field_path + [str(i)]
                        )
            elif isinstance(field_spec, dict) and value:
                # Recurse into nested structures
                self._validate_structure(value, field_spec, field_path)

    def _merge_template_data(
            self,
            target: Dict[str, Any],
            source: Dict[str, Any],
            spec: Dict[str, Any]) -> None:
        """Merge template data while respecting format specification."""
        for key, value in source.items():
            if key in spec:
                if isinstance(value, dict) and isinstance(spec[key], dict):
                    if key not in target:
                        target[key] = {}
                    self._merge_template_data(target[key], value, spec[key])
                else:
                    target[key] = copy.deepcopy(value)

    async def list_files(self, file_type: str) -> List[str]:
        """List available files of given type."""
        try:
            if not file_type:
                raise ValueError("No file type specified")

            # Get the appropriate path based on file type
            path_map = {
                "sequences": self._sequence_path,
                "parameters": self._parameter_path,
                "nozzles": self._nozzle_path,
                "patterns": self._pattern_path,
                "powders": self._powder_path,
                "runs": self._run_path
            }

            target_path = path_map.get(file_type)
            if not target_path:
                raise ValueError(f"Unknown file type: {file_type}")

            # Ensure path exists
            if not target_path.exists():
                logger.warning(f"Path does not exist for {file_type}: {target_path}")
                return []

            # Get list of YAML files
            files = [f.name for f in target_path.glob("*.yaml")]
            logger.debug(f"Found {len(files)} {file_type} files: {files}")
            return files

        except Exception as e:
            logger.error(f"Error listing {file_type} files: {e}")
            raise CoreError(f"Failed to list {file_type} files", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def load_file(self, file_type: str, name: str) -> Dict[str, Any]:
        """Load file of given type and name."""
        try:
            if not file_type or not name:
                raise ValueError("Missing file type or name")

            # Update nozzle choices before validation
            await self._update_nozzle_choices()

            file_path = self._get_path_for_type(file_type) / f"{name}.yaml"
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            # Validate file structure
            if file_type in self._file_format:
                self._validate_structure(data, self._file_format[file_type], [])

            return {
                "success": True,
                "data": data
            }

        except Exception as e:
            logger.error(f"Error loading file: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def save_file(self, file_type: str, name: str, data: Dict[str, Any]) -> Dict[str, bool]:
        """Save file of given type and name."""
        try:
            if not file_type or not name or not data:
                raise ValueError("Missing file type, name or data")

            # Update nozzle choices before validation
            await self._update_nozzle_choices()

            # Validate file structure
            if file_type in self._file_format:
                self._validate_structure(data, self._file_format[file_type], [])

            file_path = self._get_path_for_type(file_type) / f"{name}.yaml"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                yaml.dump(data, f, sort_keys=False)

            return {"success": True}

        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_file_path(self, file_type: str, name: str) -> Path:
        """Get file path with pattern subdirectory handling."""
        type_mapping = {
            "parameters": self._parameter_path,
            "nozzles": self._nozzle_path,
            "patterns": self._pattern_path,
            "sequences": self._sequence_path,
            "powders": self._powder_path
        }

        if file_type not in type_mapping:
            raise ValidationError(f"Invalid file type: {file_type}")

        if file_type == "patterns":
            for subdir in ["custom", "serpentine", "spiral"]:
                path = self._pattern_path / subdir / f"{name}.yaml"
                if path.exists():
                    return path

        return type_mapping[file_type] / f"{name}.yaml"

    def _get_path_for_type(self, file_type: str) -> Path:
        """Get directory path for file type."""
        type_mapping = {
            "parameters": self._parameter_path,
            "nozzles": self._nozzle_path,
            "patterns": self._pattern_path,
            "sequences": self._sequence_path,
            "powders": self._powder_path,
            "runs": self._run_path
        }

        if file_type not in type_mapping:
            raise ValueError(f"Invalid file type: {file_type}")

        return type_mapping[file_type]

    async def _handle_data_request(self, data: Dict[str, Any]) -> None:
        """Handle data requests."""
        try:
            request_type = data.get("request_type")
            file_type = data.get("type")
            request_id = data.get("request_id")

            logger.info(f"Handling data request: type={request_type}, file_type={file_type}, id={request_id}")

            if not request_type or not file_type:
                raise ValueError("Missing request_type or file_type")

            response = {
                "success": True,
                "request_type": request_type,
                "type": file_type,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }

            if request_type == "list":
                files = await self.list_files(file_type)
                logger.info(f"Found {len(files)} {file_type} files: {files}")
                response["data"] = {"files": files}
                await self._message_broker.publish("data/response", response)
                await self._message_broker.publish("data/state", {
                    "state": "COMPLETED",
                    "operation": "list",
                    "type": file_type,
                    "request_id": request_id
                })

            elif request_type == "load":
                name = data.get("name")
                if not name:
                    raise ValueError("Missing file name for load request")
                
                logger.info(f"Loading {file_type} file: {name}")
                
                # Get the appropriate path based on file type
                path_map = {
                    "sequences": self._sequence_path,
                    "parameters": self._parameter_path,
                    "nozzles": self._nozzle_path,
                    "patterns": self._pattern_path,
                    "powders": self._powder_path,
                    "runs": self._run_path
                }

                target_path = path_map.get(file_type)
                if not target_path:
                    raise ValueError(f"Unknown file type: {file_type}")

                file_path = target_path / f"{name}.yaml"
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")

                with open(file_path, 'r') as f:
                    file_data = yaml.safe_load(f)
                    response["data"] = file_data
                    await self._message_broker.publish("data/response", response)
                    await self._message_broker.publish("data/state", {
                        "state": "COMPLETED",
                        "operation": "load",
                        "type": file_type,
                        "name": name,
                        "request_id": request_id
                    })

        except Exception as e:
            logger.error(f"Error handling data request: {e}")
            error_response = {
                "success": False,
                "request_type": data.get("request_type"),
                "type": data.get("type"),
                "request_id": request_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._message_broker.publish("data/response", error_response)
            await self._message_broker.publish("data/state", {
                "state": "ERROR",
                "operation": data.get("request_type"),
                "type": data.get("type"),
                "error": str(e),
                "request_id": request_id
            })

    async def shutdown(self) -> None:
        """Shutdown data manager."""
        try:
            if not self._is_initialized:
                return

            # Unsubscribe from message topics
            await self._message_broker.unsubscribe("data/request", self._handle_data_request)

            self._is_initialized = False
            logger.info("Data manager shutdown complete")

        except Exception as e:
            logger.exception("Error during data manager shutdown")
            raise CoreError("Data manager shutdown failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
