from typing import Dict, Any
from loguru import logger
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ...process.validation.process_validator import ProcessValidator
from ....exceptions import ValidationError, OperationError


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

        logger.debug("Parameter manager initialized")

    async def initialize(self) -> None:
        """Initialize parameter manager."""
        try:
            if self._is_initialized:
                return

            # Subscribe to parameter messages
            await self._message_broker.subscribe(
                "parameters/load",
                self._handle_load_request
            )
            await self._message_broker.subscribe(
                "parameters/save",
                self._handle_save_request
            )

            self._is_initialized = True
            logger.info("Parameter manager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize parameter manager")
            error_context = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            raise OperationError(
                "Parameter manager initialization failed",
                "parameter",
                error_context
            )

    async def shutdown(self) -> None:
        """Shutdown parameter manager."""
        try:
            self._is_initialized = False
            logger.info("Parameter manager shutdown complete")

        except Exception as e:
            logger.exception("Error during parameter manager shutdown")
            error_context = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            raise OperationError(
                "Parameter manager shutdown failed",
                "parameter",
                error_context
            )

    async def load_parameters(self, parameters: Dict[str, Any]) -> None:
        """Load and validate parameters."""
        try:
            # Validate parameters
            validation_result = await self._process_validator.validate_parameters(parameters)

            if not validation_result["valid"]:
                error_context = {
                    "errors": validation_result["errors"],
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
                raise ValidationError(
                    "Parameter validation failed", error_context)

            # Publish loaded parameters
            await self._message_broker.publish(
                "parameters/loaded",
                {
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error loading parameters: {e}")
            await self._message_broker.publish(
                "parameters/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            error_context = {
                "error": str(e),
                "parameters": parameters,
                "timestamp": datetime.now().isoformat()
            }
            raise OperationError(
                "Parameter loading failed",
                "parameter",
                error_context
            )

    async def save_parameters(
            self, filename: str, parameters: Dict[str, Any]) -> None:
        """Save parameters to file."""
        try:
            # Validate parameters before saving
            validation_result = await self._process_validator.validate_parameters(parameters)

            if not validation_result["valid"]:
                error_context = {
                    "errors": validation_result["errors"],
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
                raise ValidationError(
                    "Parameter validation failed", error_context)

            # Publish saved parameters
            await self._message_broker.publish(
                "parameters/saved",
                {
                    "filename": filename,
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error saving parameters: {e}")
            await self._message_broker.publish(
                "parameters/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            error_context = {
                "error": str(e),
                "parameters": parameters,
                "timestamp": datetime.now().isoformat()
            }
            raise OperationError(
                "Parameter saving failed",
                "parameter",
                error_context
            )

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter load request."""
        try:
            parameters = data.get("parameters", {})
            await self.load_parameters(parameters)

        except Exception as e:
            logger.error(f"Error handling load request: {e}")
            await self._message_broker.publish(
                "parameters/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_save_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter save request."""
        try:
            filename = data.get("filename")
            parameters = data.get("parameters", {})

            if not filename:
                error_context = {
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
                raise OperationError(
                    "No filename specified for save request",
                    "parameter",
                    error_context
                )

            await self.save_parameters(filename, parameters)

        except Exception as e:
            logger.error(f"Error handling save request: {e}")
            await self._message_broker.publish(
                "parameters/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
