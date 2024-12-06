"""Pattern management component."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml
from loguru import logger

from ....exceptions import OperationError, ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker


class PatternManager:
    """Manages spray patterns and pattern generation."""

    PATTERN_TYPES = ["serpentine", "spiral", "linear", "custom"]
    VALID_DIRECTIONS = ["posX", "negX", "posY", "negY"]  # For serpentine and linear
    VALID_SPIRAL_DIRECTIONS = ["CW", "CCW"]  # For spiral

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ) -> None:
        """Initialize pattern manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager

        # Initialize paths
        self._pattern_path = Path("data/patterns")
        if not self._pattern_path.exists():
            self._pattern_path.mkdir(parents=True)

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
                "patterns/validate",
                self._handle_validation_request
            )

            self._is_initialized = True
            logger.info("Pattern manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize pattern manager: {e}")
            raise OperationError("Pattern manager initialization failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def _validate_serpentine_pattern(self, params: Dict[str, Any]) -> None:
        """Validate serpentine pattern parameters."""
        required = ["length", "width", "spacing", "direction"]
        for param in required:
            if param not in params:
                raise ValidationError(f"Missing required parameter: {param}")

        if params["length"] <= 0:
            raise ValidationError("Length must be positive")
        if params["width"] <= 0:
            raise ValidationError("Width must be positive")
        if params["spacing"] <= 0:
            raise ValidationError("Spacing must be positive")
        if params["direction"] not in self.VALID_DIRECTIONS:
            raise ValidationError(
                f"Direction must be one of: {', '.join(self.VALID_DIRECTIONS)}")

    def _validate_spiral_pattern(self, params: Dict[str, Any]) -> None:
        """Validate spiral pattern parameters."""
        required = ["diameter", "pitch", "direction"]
        for param in required:
            if param not in params:
                raise ValidationError(f"Missing required parameter: {param}")

        if params["diameter"] <= 0:
            raise ValidationError("Diameter must be positive")
        if params["pitch"] <= 0:
            raise ValidationError("Pitch must be positive")
        if params["direction"] not in self.VALID_SPIRAL_DIRECTIONS:
            raise ValidationError(
                f"Direction must be one of: {', '.join(self.VALID_SPIRAL_DIRECTIONS)}")

    def _validate_linear_pattern(self, params: Dict[str, Any]) -> None:
        """Validate linear pattern parameters."""
        required = ["length", "direction"]
        for param in required:
            if param not in params:
                raise ValidationError(f"Missing required parameter: {param}")

        if params["length"] <= 0:
            raise ValidationError("Length must be positive")
        if params["direction"] not in self.VALID_DIRECTIONS:
            raise ValidationError(
                f"Direction must be one of: {', '.join(self.VALID_DIRECTIONS)}")

    def _validate_custom_pattern(self, points: List[Dict[str, Any]]) -> None:
        """Validate custom pattern points."""
        if not points:
            raise ValidationError("Custom pattern must have at least one point")

        for point in points:
            if "position" not in point:
                raise ValidationError("Each point must have position")

            if not isinstance(point["position"], list) or len(point["position"]) != 3:
                raise ValidationError("Position must be [x, y, z] coordinates")

    async def _handle_validation_request(self, pattern: Dict[str, Any]) -> None:
        """Handle pattern validation request."""
        try:
            if "type" not in pattern:
                raise ValidationError("Pattern type not specified")

            pattern_type = pattern["type"]
            if pattern_type not in self.PATTERN_TYPES:
                raise ValidationError(f"Invalid pattern type: {pattern_type}")

            # Validate pattern parameters
            if pattern_type == "custom":
                if "points" not in pattern:
                    raise ValidationError("Custom pattern points not specified")
                self._validate_custom_pattern(pattern["points"])
            else:
                if "params" not in pattern:
                    raise ValidationError("Pattern parameters not specified")
                params = pattern["params"]
                if pattern_type == "serpentine":
                    self._validate_serpentine_pattern(params)
                elif pattern_type == "spiral":
                    self._validate_spiral_pattern(params)
                elif pattern_type == "linear":
                    self._validate_linear_pattern(params)

            # Validate against stage dimensions
            await self._validate_pattern_bounds(pattern)

            # Publish validation success
            await self._message_broker.publish(
                "patterns/validated",
                {
                    "valid": True,
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except ValidationError as e:
            logger.error(f"Pattern validation failed: {e}")
            await self._message_broker.publish(
                "patterns/validated",
                {
                    "valid": False,
                    "error": str(e),
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _create_pattern_filename(self, pattern_data: Dict[str, Any]) -> str:
        """Create standardized pattern filename."""
        pattern_type = pattern_data["type"]
        params = pattern_data["params"]

        # Create parameter string based on pattern type
        if pattern_type == "serpentine":
            param_str = (
                f"{params['spacing']}mm-{params['length']}mm-{params['width']}mm-"
                f"{params['direction']}"
            )
        elif pattern_type == "spiral":
            param_str = (
                f"{params['pitch']}mm-{params['diameter']}mm-"
                f"{params['direction']}"
            )
        elif pattern_type == "linear":
            param_str = f"{params['length']}mm-{params['direction']}"
        else:  # custom
            # Use provided name or generate one
            if "name" in params:
                return f"custom_{params['name']}.yaml"
            else:
                param_str = f"{len(params['points'])}points"

        # Generate unique name
        base_name = f"{pattern_type}_{param_str}"
        counter = 1
        while True:
            if counter == 1:
                filename = f"{base_name}.yaml"
            else:
                filename = f"{base_name}_{counter}.yaml"

            if not (self._pattern_path / filename).exists():
                return filename
            counter += 1

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle pattern load request."""
        try:
            filename = data.get("filename")
            if not filename:
                raise ValidationError("No filename specified for load request")

            # Load pattern file
            pattern_path = self._pattern_path / filename
            if not pattern_path.exists():
                raise ValidationError(f"Pattern file not found: {filename}")

            with open(pattern_path, 'r') as f:
                pattern_data = yaml.safe_load(f)

            # Validate pattern
            await self._handle_validation_request(pattern_data["pattern"])

            # Publish loaded pattern
            await self._message_broker.publish(
                "patterns/loaded",
                {
                    "pattern": pattern_data["pattern"],
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
            pattern_data = data.get("pattern", {})
            if not pattern_data:
                raise ValidationError("No pattern data provided")

            # Validate pattern
            await self._handle_validation_request(pattern_data)

            # Create filename from pattern type and parameters
            filename = self._create_pattern_filename(pattern_data)

            # Save pattern file
            pattern_path = self._pattern_path / filename
            with open(pattern_path, 'w') as f:
                yaml.safe_dump({"pattern": pattern_data}, f, sort_keys=False)

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

    async def _validate_pattern_bounds(self, pattern: Dict[str, Any]) -> None:
        """Validate pattern bounds against stage dimensions."""
        try:
            # Get stage dimensions from hardware config
            hw_config = await self._config_manager.get_config("hardware")
            stage_dims = hw_config.get("stage", {}).get("dimensions", {})

            # Get pattern bounds based on type
            bounds = self._get_pattern_bounds(pattern)

            # Check bounds against stage dimensions
            for axis in ["x", "y", "z"]:
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
        """Get pattern bounds based on type."""
        pattern_type = pattern["type"]
        params = pattern["params"]

        if pattern_type == "custom":
            points = params["points"]
            x_coords = [p["position"][0] for p in points]
            y_coords = [p["position"][1] for p in points]
            z_coords = [p["position"][2] for p in points]
            return {
                "min_x": min(x_coords),
                "max_x": max(x_coords),
                "min_y": min(y_coords),
                "max_y": max(y_coords),
                "min_z": min(z_coords),
                "max_z": max(z_coords)
            }

        # For relative patterns, bounds are based on pattern dimensions
        if pattern_type == "serpentine":
            length = params["length"]
            width = params["width"]
            direction = params["direction"]

            if direction in ["posX", "negX"]:
                return {
                    "min_x": 0 if direction == "posX" else -length,
                    "max_x": length if direction == "posX" else 0,
                    "min_y": 0,
                    "max_y": width,
                    "min_z": 0,
                    "max_z": 0
                }
            else:  # posY or negY
                return {
                    "min_x": 0,
                    "max_x": width,
                    "min_y": 0 if direction == "posY" else -length,
                    "max_y": length if direction == "posY" else 0,
                    "min_z": 0,
                    "max_z": 0
                }

        elif pattern_type == "spiral":
            radius = params["diameter"] / 2
            return {
                "min_x": -radius,
                "max_x": radius,
                "min_y": -radius,
                "max_y": radius,
                "min_z": 0,
                "max_z": 0
            }

        elif pattern_type == "linear":
            length = params["length"]
            direction = params["direction"]

            if direction in ["posX", "negX"]:
                return {
                    "min_x": 0 if direction == "posX" else -length,
                    "max_x": length if direction == "posX" else 0,
                    "min_y": 0,
                    "max_y": 0,
                    "min_z": 0,
                    "max_z": 0
                }
            else:  # posY or negY
                return {
                    "min_x": 0,
                    "max_x": 0,
                    "min_y": 0 if direction == "posY" else -length,
                    "max_y": length if direction == "posY" else 0,
                    "min_z": 0,
                    "max_z": 0
                }

        else:
            raise ValidationError(f"Unknown pattern type: {pattern_type}")
