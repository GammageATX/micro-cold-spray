from datetime import datetime
from typing import Any, Dict
from pathlib import Path
import yaml

from loguru import logger

from micro_cold_spray.core.exceptions import OperationError, ValidationError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.process.validation.process_validator import ProcessValidator


class ParameterManager:
    """Manages process parameters and validation."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        process_validator: ProcessValidator
    ):
        """Initialize manager with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._process_validator = process_validator
        self._is_initialized = False
        self._current_parameters = None
        self._current_file = None
        self._is_modified = False

        logger.debug("Parameter manager initialized")

    async def initialize(self) -> None:
        """Initialize parameter manager."""
        try:
            if self._is_initialized:
                return

            # Subscribe to parameter request topic
            await self._message_broker.subscribe(
                "parameter/request",
                self._handle_parameter_request
            )

            # Publish initial state
            await self._publish_parameter_state("NONE")

            self._is_initialized = True
            logger.info("Parameter manager initialization complete")

        except Exception as e:
            error_msg = f"Failed to initialize parameter manager: {str(e)}"
            logger.error(error_msg)
            await self._message_broker.publish("error", {
                "source": "parameter_manager",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            raise OperationError("parameter_manager", error_msg)

    async def _handle_parameter_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter request messages."""
        request_id = data.get("request_id", "")
        try:
            request_type = data.get("request_type")
            if not request_type:
                raise ValidationError("Missing request_type")

            if request_type == "load":
                await self._handle_load_request(data)
            elif request_type == "save":
                await self._handle_save_request(data)
            elif request_type == "validate":
                await self._handle_validation_request(data)
            elif request_type == "edit":
                await self._handle_edit_request(data)
            else:
                raise ValidationError(f"Invalid request_type: {request_type}")

            # Send success response
            await self._message_broker.publish("parameter/response", {
                "request_id": request_id,
                "success": True,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error handling parameter request: {error_msg}")

            # Send error response
            await self._message_broker.publish("parameter/response", {
                "request_id": request_id,
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })

            # Publish to error topic
            await self._message_broker.publish("error", {
                "source": "parameter_manager",
                "error": error_msg,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter load request."""
        try:
            # Get parameter file path
            if "file" not in data:
                raise ValidationError("No parameter file specified")

            file_path = Path(data["file"])
            if not file_path.exists():
                raise ValidationError(f"Parameter file not found: {file_path}")

            # Load parameters from file
            with open(file_path, 'r') as f:
                parameters = yaml.safe_load(f)

            # Validate parameters
            result = await self._process_validator.validate_parameters(parameters)

            # Update internal state
            self._current_parameters = parameters
            self._current_file = file_path
            self._is_modified = False

            # Update parameter state
            await self._publish_parameter_state("LOADED")

            # If validation failed, publish validation response
            if not result["valid"]:
                await self._message_broker.publish("validation/response", {
                    "request_type": "parameters",
                    "result": result,
                    "data": parameters
                })
                raise ValidationError(f"Parameter validation failed: {result['errors']}")

        except Exception as e:
            error_msg = f"Failed to load parameters: {str(e)}"
            logger.error(error_msg)
            raise OperationError("parameter_manager", error_msg)

    async def _handle_save_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter save request."""
        try:
            # Get parameters to save
            if "parameters" not in data:
                raise ValidationError("No parameters provided for save request")

            # Get filename
            if "name" not in data:
                raise ValidationError("No filename specified for save request")

            # Validate parameters
            result = await self._process_validator.validate_parameters(data["parameters"])
            if not result["valid"]:
                raise ValidationError(f"Parameter validation failed: {result['errors']}")

            # Create parameters directory if it doesn't exist
            save_dir = Path("data/parameters")
            save_dir.mkdir(parents=True, exist_ok=True)

            # Save parameters to file
            file_path = save_dir / f"{data['name']}.yaml"
            with open(file_path, 'w') as f:
                yaml.safe_dump(data["parameters"], f)

            # Update internal state
            self._current_parameters = data["parameters"]
            self._current_file = file_path
            self._is_modified = False

            # Update parameter state
            await self._publish_parameter_state("SAVED")

        except Exception as e:
            error_msg = f"Failed to save parameters: {str(e)}"
            logger.error(error_msg)
            raise OperationError("parameter_manager", error_msg)

    async def _handle_edit_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter edit request."""
        try:
            if "parameters" not in data:
                raise ValidationError("No parameters provided for edit")

            # Validate parameters
            result = await self._process_validator.validate_parameters(data["parameters"])
            if not result["valid"]:
                raise ValidationError(f"Parameter validation failed: {result['errors']}")

            # Update internal state
            self._current_parameters = data["parameters"]
            self._is_modified = True

            # Update parameter state
            await self._publish_parameter_state("MODIFIED")

        except Exception as e:
            error_msg = f"Failed to edit parameters: {str(e)}"
            logger.error(error_msg)
            raise OperationError("parameter_manager", error_msg)

    async def _handle_validation_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter validation request."""
        try:
            # Validate parameters
            result = await self._process_validator.validate_parameters(data["parameters"])

            # Publish validation response
            await self._message_broker.publish("validation/response", {
                "request_type": "parameters",
                "result": result,
                "data": data["parameters"]
            })

            if not result["valid"]:
                raise ValidationError(f"Parameter validation failed: {result['errors']}")

        except Exception as e:
            error_msg = f"Failed to validate parameters: {str(e)}"
            logger.error(error_msg)
            raise OperationError("parameter_manager", error_msg)

    async def _publish_parameter_state(self, state: str) -> None:
        """Publish parameter state update."""
        await self._message_broker.publish(
            "parameter/state",
            {
                "state": state,
                "file": str(self._current_file) if self._current_file else None,
                "parameters": self._current_parameters,
                "is_modified": self._is_modified,
                "timestamp": datetime.now().isoformat()
            }
        )
