"""Pattern management component."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from ....components.process.validation.process_validator import ProcessValidator
from ....exceptions import OperationError, ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker


class PatternManager:
    """Manages spray patterns and pattern generation."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        process_validator: ProcessValidator
    ) -> None:
        """Initialize pattern manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._process_validator = process_validator

        # Initialize paths
        self._pattern_path = Path("data/patterns")
        self._custom_path = Path("data/patterns/custom")

        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize pattern manager."""
        try:
            if self._is_initialized:
                return

            # Create directories if they don't exist
            self._pattern_path.mkdir(parents=True, exist_ok=True)
            self._custom_path.mkdir(parents=True, exist_ok=True)

            # Subscribe to pattern messages
            await self._message_broker.subscribe(
                "patterns/load",
                self._handle_load_request
            )
            await self._message_broker.subscribe(
                "patterns/save",
                self._handle_save_request
            )

            self._is_initialized = True
            logger.info("Pattern manager initialized")

        except Exception as e:
            logger.exception("Failed to initialize pattern manager")
            raise OperationError("Pattern manager initialization failed", "pattern", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def shutdown(self) -> None:
        """Shutdown pattern manager."""
        try:
            self._is_initialized = False
            logger.info("Pattern manager shutdown complete")

        except Exception as e:
            logger.exception("Error during pattern manager shutdown")
            raise OperationError(
                "Pattern manager shutdown failed", "pattern", {
                    "error": str(e)})

    async def _validate_pattern_params(
            self, pattern_data: Dict[str, Any]) -> None:
        """Validate pattern parameters against rules."""
        try:
            # Get validation rules from process config
            process_config = await self._config_manager.get_config("process")
            validation_rules = process_config.get(
                "validation", {}).get("patterns", {})

            pattern_type = pattern_data["pattern"]["type"]
            params = pattern_data["pattern"]["params"]

            if pattern_type not in validation_rules:
                raise OperationError(
                    f"Unknown pattern type: {pattern_type}", "pattern", {
                        "type": pattern_type, "timestamp": datetime.now().isoformat()})

            type_rules = validation_rules[pattern_type]

            # Check required fields
            required = type_rules.get("required_fields", {}).get("fields", [])
            for field in required:
                if field not in params:
                    raise ValidationError(type_rules["required_fields"]["message"], {
                        "pattern_type": pattern_type,
                        "missing_field": field,
                        "timestamp": datetime.now().isoformat()
                    })

            # Check for unknown fields
            optional = type_rules.get("optional_fields", {}).get("fields", [])
            for field in params.keys():
                if field not in required and field not in optional:
                    raise ValidationError(type_rules["optional_fields"]["message"], {
                        "pattern_type": pattern_type,
                        "unknown_field": field,
                        "timestamp": datetime.now().isoformat()
                    })

        except Exception as e:
            logger.error(f"Error validating pattern parameters: {e}")
            raise OperationError("Failed to validate pattern parameters", "pattern", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _validate_sprayable_area(
            self, pattern_data: Dict[str, Any]) -> None:
        """Validate pattern stays within sprayable area."""
        try:
            # Get stage dimensions from hardware config
            hardware_config = await self._config_manager.get_config("hardware")
            stage_dims = hardware_config["physical"]["stage"]["dimensions"]

            # Get pattern bounds based on type
            pattern_type = pattern_data["pattern"]["type"]
            params = pattern_data["pattern"]["params"]

            if pattern_type == "serpentine":
                origin = params["origin"]
                length = params["length"]

                # Calculate pattern bounds
                x_min = origin[0]
                x_max = origin[0] + length
                y_min = origin[1]
                y_max = origin[1] + params["spacing"]

                # Validate bounds against stage dimensions
                if (x_min < 0 or x_max > stage_dims["x"]
                        or y_min < 0 or y_max > stage_dims["y"]):

                    raise ValidationError(
                        f"Pattern exceeds stage dimensions: "
                        f"[0, {stage_dims['x']}] x [0, {stage_dims['y']}]",
                        {
                            "pattern_bounds": {
                                "x": [x_min, x_max],
                                "y": [y_min, y_max]
                            },
                            "stage_dims": stage_dims
                        }
                    )

        except Exception as e:
            logger.error(f"Error validating sprayable area: {e}")
            raise OperationError(
                "Failed to validate sprayable area", "pattern", {
                    "error": str(e)})

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle pattern load request."""
        try:
            pattern_data = data.get("pattern", {})

            # Validate pattern parameters
            await self._validate_pattern_params(pattern_data)

            # Validate sprayable area
            await self._validate_sprayable_area(pattern_data)

            # Publish loaded pattern
            await self._message_broker.publish(
                "patterns/loaded",
                {
                    "pattern": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling load request: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_save_request(self, data: Dict[str, Any]) -> None:
        """Handle pattern save request."""
        try:
            filename = data.get("filename")
            pattern_data = data.get("pattern", {})

            if not filename:
                error_context = {
                    "pattern": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
                raise OperationError(
                    "No filename specified for save request",
                    "pattern",
                    error_context
                )

            # Validate pattern parameters
            await self._validate_pattern_params(pattern_data)

            # Validate sprayable area
            await self._validate_sprayable_area(pattern_data)

            # Publish saved pattern
            await self._message_broker.publish(
                "patterns/saved",
                {
                    "filename": filename,
                    "pattern": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling save request: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
