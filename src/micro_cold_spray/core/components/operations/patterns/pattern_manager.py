"""Pattern management component."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from ....components.process.validation.process_validator import ProcessValidator
from ....exceptions import OperationError, ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker
from ....exceptions import CoreError


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

            # Subscribe to pattern messages
            await self._message_broker.subscribe(
                "patterns/load",
                self._handle_load_request
            )
            await self._message_broker.subscribe(
                "patterns/save",
                self._handle_save_request
            )
            await self._message_broker.subscribe(
                "pattern/validate",
                self._handle_validation_request
            )

            self._is_initialized = True
            logger.info("Pattern manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize pattern manager: {e}")
            raise CoreError("Pattern manager initialization failed", {
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

    async def _handle_validation_request(self, pattern: Dict[str, Any]) -> None:
        """Handle pattern validation request."""
        try:
            # Validate pattern type
            if "type" not in pattern:
                raise ValidationError("Pattern type not specified")

            pattern_type = pattern["type"]
            if pattern_type not in ["line", "rectangle", "circle"]:
                raise ValidationError(f"Invalid pattern type: {pattern_type}")

            # Validate pattern parameters
            if "parameters" not in pattern:
                raise ValidationError("Pattern parameters not specified")

            params = pattern["parameters"]
            if pattern_type == "line":
                self._validate_line_pattern(params)
            elif pattern_type == "rectangle":
                self._validate_rectangle_pattern(params)
            elif pattern_type == "circle":
                self._validate_circle_pattern(params)

            # Validate against stage dimensions
            await self._validate_pattern_bounds(pattern)

            # Publish validation success
            await self._message_broker.publish(
                "pattern/validation",
                {
                    "valid": True,
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except ValidationError as e:
            logger.error(f"Pattern validation failed: {e}")
            await self._message_broker.publish(
                "pattern/validation",
                {
                    "valid": False,
                    "error": str(e),
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error validating pattern: {e}")
            await self._message_broker.publish(
                "pattern/validation",
                {
                    "valid": False,
                    "error": str(e),
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _validate_line_pattern(self, params: Dict[str, Any]) -> None:
        """Validate line pattern parameters."""
        if "start" not in params or "end" not in params:
            raise ValidationError("Line pattern must have start and end points")

        for point in [params["start"], params["end"]]:
            if "x" not in point or "y" not in point:
                raise ValidationError("Points must have x and y coordinates")

    def _validate_rectangle_pattern(self, params: Dict[str, Any]) -> None:
        """Validate rectangle pattern parameters."""
        if "origin" not in params:
            raise ValidationError("Rectangle pattern must have origin point")
        if "width" not in params or "height" not in params:
            raise ValidationError(
                "Rectangle pattern must have width and height")

        origin = params["origin"]
        if "x" not in origin or "y" not in origin:
            raise ValidationError("Origin must have x and y coordinates")

        if params["width"] <= 0 or params["height"] <= 0:
            raise ValidationError(
                "Rectangle width and height must be positive")

    def _validate_circle_pattern(self, params: Dict[str, Any]) -> None:
        """Validate circle pattern parameters."""
        if "center" not in params:
            raise ValidationError("Circle pattern must have center point")
        if "radius" not in params:
            raise ValidationError("Circle pattern must have radius")

        center = params["center"]
        if "x" not in center or "y" not in center:
            raise ValidationError("Center must have x and y coordinates")

        if params["radius"] <= 0:
            raise ValidationError("Circle radius must be positive")

    async def _validate_pattern_bounds(self, pattern: Dict[str, Any]) -> None:
        """Validate pattern bounds against stage dimensions."""
        try:
            # Get stage dimensions from hardware config
            hw_config = await self._config_manager.get_config("hardware")
            stage_dims = hw_config.get("stage", {}).get("dimensions", {})

            # Get pattern bounds
            bounds = self._get_pattern_bounds(pattern)

            # Check bounds against stage dimensions
            for axis in ["x", "y"]:
                axis_dims = stage_dims.get(axis, {})
                min_pos = axis_dims.get("min", 0)
                max_pos = axis_dims.get("max", 200)  # Default to 200mm

                if bounds[f"min_{axis}"] < min_pos:
                    raise ValidationError(
                        f"Pattern extends below minimum {axis} position")
                if bounds[f"max_{axis}"] > max_pos:
                    raise ValidationError(
                        f"Pattern extends above maximum {axis} position")

        except Exception as e:
            logger.error(f"Error validating pattern bounds: {e}")
            raise ValidationError(f"Pattern bounds validation failed: {str(e)}")

    def _get_pattern_bounds(self, pattern: Dict[str, Any]) -> Dict[str, float]:
        """Get pattern bounds."""
        pattern_type = pattern["type"]
        params = pattern["parameters"]

        if pattern_type == "line":
            start = params["start"]
            end = params["end"]
            return {
                "min_x": min(start["x"], end["x"]),
                "max_x": max(start["x"], end["x"]),
                "min_y": min(start["y"], end["y"]),
                "max_y": max(start["y"], end["y"])
            }
        elif pattern_type == "rectangle":
            origin = params["origin"]
            width = params["width"]
            height = params["height"]
            return {
                "min_x": origin["x"],
                "max_x": origin["x"] + width,
                "min_y": origin["y"],
                "max_y": origin["y"] + height
            }
        elif pattern_type == "circle":
            center = params["center"]
            radius = params["radius"]
            return {
                "min_x": center["x"] - radius,
                "max_x": center["x"] + radius,
                "min_y": center["y"] - radius,
                "max_y": center["y"] + radius
            }
        else:
            raise ValidationError(f"Unknown pattern type: {pattern_type}")

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
