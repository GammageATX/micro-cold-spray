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

        # Data paths will be set during initialization from application config
        self._run_path: Optional[Path] = None
        self._parameter_path: Optional[Path] = None
        self._nozzle_path: Optional[Path] = None
        self._pattern_path: Optional[Path] = None
        self._sequence_path: Optional[Path] = None
        self._powder_path: Optional[Path] = None

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

            # Set up data directories from config
            self._run_path = Path(data_paths.get("runs", "data/runs"))
            self._parameter_path = Path(data_paths.get("parameters", "data/parameters"))
            self._nozzle_path = self._parameter_path / "nozzles"
            self._pattern_path = Path(data_paths.get("patterns", {}).get("root", "data/patterns"))
            self._sequence_path = Path(data_paths.get("sequences", "data/sequences"))
            self._powder_path = Path(data_paths.get("powders", "data/powders"))

            # Create only the base directories
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

            # Subscribe to message topics
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            await self._message_broker.subscribe("data/list_files", self._handle_list_files_request)
            await self._message_broker.subscribe("data/load", self._handle_load_request)
            await self._message_broker.subscribe("data/save", self._handle_save_request)
            await self._message_broker.subscribe("data/delete", self._handle_delete_request)

            self._is_initialized = True
            logger.info("Data manager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize data manager")
            raise CoreError("Data manager initialization failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def list_files(self, file_type: str) -> Dict[str, Any]:
        """List available files of given type."""
        try:
            if not file_type:
                raise ValidationError("No file type specified")

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
                logger.info(f"Searching pattern directories: {type_mapping[file_type]}")
                for subdir in type_mapping[file_type].values():
                    if subdir.exists():
                        logger.info(f"Checking directory: {subdir}")
                        for file_path in subdir.glob("*.yaml"):
                            # Just use the filename without directory
                            files.append(file_path.stem)
                            logger.info(f"Found pattern file: {file_path}")
            else:
                # For other types, list files directly
                base_path = type_mapping[file_type]
                if base_path.exists():
                    # Skip library and history directories for parameters
                    if file_type == "parameters":
                        for file_path in base_path.glob("*.yaml"):
                            # Only include files in the root parameters directory
                            if file_path.parent == base_path:
                                files.append(file_path.stem)
                    else:
                        for file_path in base_path.glob("*.yaml"):
                            files.append(file_path.stem)

            # Sort files for consistent ordering
            files.sort()
            logger.info(f"Final file list for {file_type}: {files}")

            # Add empty option for dropdowns
            files.insert(0, {"name": "", "path": "", "metadata": {}})

            return {"files": files}

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {"files": []}

    async def _handle_list_files_request(self, data: Dict[str, Any]) -> None:
        """Handle request to list files of a certain type."""
        try:
            file_type = data.get("type")
            logger.debug(f"Handling list files request for type: {file_type}")

            # Map file type to directory
            type_mapping = {
                "parameters": self._parameter_path,
                "nozzles": self._nozzle_path,
                "patterns": self._pattern_path,
                "sequences": self._sequence_path,
                "powders": self._powder_path
            }

            logger.info(f"Directory mapping for {file_type}: {type_mapping[file_type]}")

            if file_type not in type_mapping:
                raise ValidationError(f"Invalid file type: {file_type}")

            files = []
            if isinstance(type_mapping[file_type], dict):
                # For patterns, list files from all subdirectories
                logger.info(f"Searching pattern directories: {type_mapping[file_type]}")
                for subdir in type_mapping[file_type].values():
                    if subdir.exists():
                        logger.info(f"Checking directory: {subdir}")
                        for file_path in subdir.glob("*.yaml"):
                            # Just use the filename without directory
                            files.append(file_path.stem)
                            logger.info(f"Found pattern file: {file_path}")
            else:
                # For other types, list files directly
                base_path = type_mapping[file_type]
                if base_path.exists():
                    # Skip library and history directories for parameters
                    if file_type == "parameters":
                        for file_path in base_path.glob("*.yaml"):
                            # Only include files in the root parameters directory
                            if file_path.parent == base_path:
                                files.append(file_path.stem)
                    else:
                        for file_path in base_path.glob("*.yaml"):
                            files.append(file_path.stem)

            # Sort files for consistent ordering
            files.sort()
            logger.info(f"Final file list for {file_type}: {files}")

            # Send response
            await self._message_broker.publish("data/files/listed", {
                "type": file_type,
                "files": files
            })
            logger.info("Sent file list update")

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            await self._message_broker.publish(
                "data/files/error",
                {
                    "type": file_type,
                    "error": str(e)
                }
            )

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

    async def shutdown(self) -> None:
        """Shutdown data manager."""
        try:
            # Unsubscribe from message topics
            await self._message_broker.unsubscribe("tag/update", self._handle_tag_update)
            await self._message_broker.unsubscribe("data/list_files", self._handle_list_files_request)
            await self._message_broker.unsubscribe("data/load", self._handle_load_request)
            await self._message_broker.unsubscribe("data/save", self._handle_save_request)
            await self._message_broker.unsubscribe("data/delete", self._handle_delete_request)

            self._is_initialized = False
            logger.info("Data manager shutdown complete")

        except Exception as e:
            logger.exception("Error during data manager shutdown")
            raise CoreError("Data manager shutdown failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def load_file(self, file_type: str, name: str) -> Dict[str, Any]:
        """Load file of given type."""
        try:
            if not file_type or not name:
                raise ValidationError("Missing file type or name")

            # Map file type to directory
            type_mapping = {
                "parameters": self._parameter_path,
                "nozzles": self._nozzle_path,
                "patterns": self._pattern_path,
                "sequences": self._sequence_path,
                "powders": self._powder_path
            }

            if file_type not in type_mapping:
                raise ValidationError(f"Invalid file type: {file_type}")

            # Handle pattern subdirectories
            if file_type == "patterns":
                # Check each pattern subdirectory
                for subdir in ["custom", "serpentine", "spiral"]:
                    file_path = self._pattern_path / subdir / f"{name}.yaml"
                    if file_path.exists():
                        break
            else:
                file_path = type_mapping[file_type] / f"{name}.yaml"

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {name}")

            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            return {"value": data}

        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return {"error": str(e)}

    async def save_file(self, file_type: str, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save file of given type."""
        try:
            if not file_type or not name or not data:
                raise ValidationError("Missing file type, name or data")

            # Map file type to directory
            type_mapping = {
                "parameters": self._parameter_path,
                "nozzles": self._nozzle_path,
                "patterns": self._pattern_path,
                "sequences": self._sequence_path,
                "powders": self._powder_path
            }

            if file_type not in type_mapping:
                raise ValidationError(f"Invalid file type: {file_type}")

            # Handle pattern subdirectories
            if file_type == "patterns":
                # Save to custom directory by default
                file_path = self._pattern_path / "custom" / f"{name}.yaml"
            else:
                file_path = type_mapping[file_type] / f"{name}.yaml"

            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)

            return {"success": True}

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return {"error": str(e)}

    async def delete_file(self, file_type: str, name: str) -> Dict[str, Any]:
        """Delete file of given type."""
        try:
            if not file_type or not name:
                raise ValidationError("Missing file type or name")

            # Map file type to directory
            type_mapping = {
                "parameters": self._parameter_path,
                "nozzles": self._nozzle_path,
                "patterns": self._pattern_path,
                "sequences": self._sequence_path,
                "powders": self._powder_path
            }

            if file_type not in type_mapping:
                raise ValidationError(f"Invalid file type: {file_type}")

            # Handle pattern subdirectories
            if file_type == "patterns":
                # Check each pattern subdirectory
                for subdir in ["custom", "serpentine", "spiral"]:
                    file_path = self._pattern_path / subdir / f"{name}.yaml"
                    if file_path.exists():
                        file_path.unlink()
                        return {"success": True}
                raise FileNotFoundError(f"Pattern not found: {name}")
            else:
                file_path = type_mapping[file_type] / f"{name}.yaml"
                if file_path.exists():
                    file_path.unlink()
                    return {"success": True}
                else:
                    raise FileNotFoundError(f"File not found: {name}")

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {"error": str(e)}

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle request to load a file."""
        try:
            file_type = data.get("type")
            name = data.get("name")
            logger.debug(f"Handling load request for {file_type}: {name}")

            if not file_type or not name:
                raise ValidationError("Missing file type or name")

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

            # Get file path
            if isinstance(type_mapping[file_type], dict):
                # For patterns, need to find in subdirectories
                file_path = None
                for subdir in type_mapping[file_type].values():
                    test_path = subdir / f"{name}.yaml"
                    if test_path.exists():
                        file_path = test_path
                        break
                if not file_path:
                    raise FileNotFoundError(f"Pattern not found: {name}")
            else:
                file_path = type_mapping[file_type] / f"{name}.yaml"
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {name}")

            # Load file
            with open(file_path, "r") as f:
                file_data = yaml.safe_load(f)

            # Send response
            await self._message_broker.publish(
                "data/loaded",
                {
                    "type": file_type,
                    "name": name,
                    "value": file_data
                }
            )
            logger.debug(f"Loaded {file_type} file: {name}")

        except Exception as e:
            logger.error(f"Error loading file: {e}")
            await self._message_broker.publish(
                "data/error",
                {
                    "type": file_type,
                    "name": name,
                    "error": str(e)
                }
            )

    async def _handle_save_request(self, data: Dict[str, Any]) -> None:
        """Handle request to save a file."""
        try:
            file_type = data.get("type")
            name = data.get("name")
            value = data.get("value")
            logger.debug(f"Handling save request for {file_type}: {name}")

            if not file_type or not name or value is None:
                raise ValidationError("Missing file type, name, or value")

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

            # Get file path
            if isinstance(type_mapping[file_type], dict):
                # For patterns, save to custom directory
                file_path = type_mapping[file_type]["custom"] / f"{name}.yaml"
            else:
                file_path = type_mapping[file_type] / f"{name}.yaml"

            # Save file
            with open(file_path, "w") as f:
                yaml.safe_dump(value, f, default_flow_style=False)

            # Send response
            await self._message_broker.publish(
                "data/saved",
                {
                    "type": file_type,
                    "name": name
                }
            )
            logger.debug(f"Saved {file_type} file: {name}")

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            await self._message_broker.publish(
                "data/error",
                {
                    "type": file_type,
                    "name": name,
                    "error": str(e)
                }
            )

    async def _handle_delete_request(self, data: Dict[str, Any]) -> None:
        """Handle request to delete a file."""
        try:
            file_type = data.get("type")
            name = data.get("name")
            logger.debug(f"Handling delete request for {file_type}: {name}")

            if not file_type or not name:
                raise ValidationError("Missing file type or name")

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

            # Get file path
            if isinstance(type_mapping[file_type], dict):
                # For patterns, need to find in subdirectories
                file_path = None
                for subdir in type_mapping[file_type].values():
                    test_path = subdir / f"{name}.yaml"
                    if test_path.exists():
                        file_path = test_path
                        break
                if not file_path:
                    raise FileNotFoundError(f"Pattern not found: {name}")
            else:
                file_path = type_mapping[file_type] / f"{name}.yaml"
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {name}")

            # Delete file
            file_path.unlink()

            # Send response
            await self._message_broker.publish(
                "data/deleted",
                {
                    "type": file_type,
                    "name": name
                }
            )
            logger.debug(f"Deleted {file_type} file: {name}")

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            await self._message_broker.publish(
                "data/error",
                {
                    "type": file_type,
                    "name": name,
                    "error": str(e)
                }
            )
