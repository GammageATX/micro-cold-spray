"""Pattern management component."""
from typing import Dict, Any, List, Optional
from loguru import logger
import asyncio
from datetime import datetime
from pathlib import Path
import yaml
import csv

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ....exceptions import PatternError

class PatternManager:
    """Manages spray patterns and pattern generation."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        pattern_path: Path = Path("data/patterns/library"),
        custom_path: Path = Path("data/patterns/custom")
    ) -> None:
        """Initialize pattern manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._pattern_path = pattern_path
        self._custom_path = custom_path
        self._loaded_pattern: Optional[Dict[str, Any]] = None
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
            raise PatternError(f"Pattern manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown pattern manager."""
        try:
            self._is_initialized = False
            logger.info("Pattern manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during pattern manager shutdown")
            raise PatternError(f"Pattern manager shutdown failed: {str(e)}") from e

    def get_available_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get list of available patterns by type."""
        try:
            patterns = {
                "serpentine": [],
                "spiral": [],
                "custom": []
            }
            
            # Load library patterns
            for pattern_type in ["serpentine", "spiral"]:
                type_path = self._pattern_path / pattern_type
                for file in type_path.glob("*.yaml"):
                    with open(file, 'r') as f:
                        pattern = yaml.safe_load(f)
                        patterns[pattern_type].append({
                            "name": pattern["pattern"]["metadata"]["name"],
                            "file": file.name,
                            "type": pattern_type
                        })
                        
            # Load custom patterns
            for file in self._custom_path.glob("*.csv"):
                patterns["custom"].append({
                    "name": file.stem,
                    "file": file.name,
                    "type": "custom"
                })
                
            return patterns
            
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            raise PatternError(f"Failed to load patterns: {str(e)}") from e

    async def load_pattern(self, pattern_type: str, filename: str) -> Dict[str, Any]:
        """Load pattern file."""
        try:
            if pattern_type == "custom":
                file_path = self._custom_path / filename
                pattern = self._load_custom_pattern(file_path)
            else:
                file_path = self._pattern_path / pattern_type / filename
                with open(file_path, 'r') as f:
                    pattern = yaml.safe_load(f)
                    
            self._loaded_pattern = pattern
            
            # Publish pattern loaded event
            await self._message_broker.publish(
                "patterns/loaded",
                {
                    "pattern": pattern,
                    "type": pattern_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error loading pattern: {e}")
            raise PatternError(f"Failed to load pattern: {str(e)}") from e

    def _load_custom_pattern(self, file_path: Path) -> Dict[str, Any]:
        """Load custom pattern from CSV."""
        try:
            moves = []
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    moves.append({
                        "x": float(row["x"]),
                        "y": float(row["y"]),
                        "z": float(row["z"]),
                        "velocity": float(row["velocity"]),
                        "dwell": float(row["dwell"]),
                        "spray_on": row["spray_on"].lower() == "true"
                    })
                    
            return {
                "pattern": {
                    "metadata": {
                        "name": file_path.stem,
                        "type": "custom"
                    },
                    "moves": moves
                }
            }
            
        except Exception as e:
            logger.error(f"Error loading custom pattern: {e}")
            raise PatternError(f"Failed to load custom pattern: {str(e)}") from e

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle pattern load request."""
        try:
            pattern_type = data["type"]
            filename = data["filename"]
            await self.load_pattern(pattern_type, filename)
            
        except Exception as e:
            logger.error(f"Error handling load request: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "context": "load_request",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_save_request(self, data: Dict[str, Any]) -> None:
        """Handle pattern save request."""
        try:
            pattern = data["pattern"]
            pattern_type = data["type"]
            filename = data["filename"]
            
            if pattern_type == "custom":
                file_path = self._custom_path / filename
                self._save_custom_pattern(pattern, file_path)
            else:
                file_path = self._pattern_path / pattern_type / filename
                with open(file_path, 'w') as f:
                    yaml.safe_dump(pattern, f, sort_keys=False)
                    
            logger.info(f"Saved pattern to {filename}")
            
            # Publish pattern saved event
            await self._message_broker.publish(
                "patterns/saved",
                {
                    "filename": filename,
                    "type": pattern_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling save request: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "context": "save_request",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def generate_serpentine(
        self,
        origin: List[float],
        length: float,
        spacing: float,
        speed: float,
        z_height: float,
        acceleration: float,
        direction: str = "x_first",
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate serpentine pattern."""
        try:
            # Validate inputs
            await self._validate_pattern_params({
                "origin": origin,
                "length": length,
                "spacing": spacing,
                "speed": speed,
                "z_height": z_height,
                "acceleration": acceleration
            })

            # Generate pattern metadata
            pattern = {
                "pattern": {
                    "metadata": {
                        "name": name or f"Serpentine_{spacing}mm_{speed}mms",
                        "version": "1.0",
                        "created": datetime.now().isoformat(),
                        "description": f"Generated serpentine pattern with {spacing}mm spacing"
                    },
                    "type": "serpentine",
                    "params": {
                        "origin": origin,
                        "length": length,
                        "spacing": spacing,
                        "speed": speed,
                        "z_height": z_height,
                        "acceleration": acceleration,
                        "direction": direction
                    }
                }
            }

            return pattern

        except Exception as e:
            logger.error(f"Error generating serpentine pattern: {e}")
            raise PatternError(f"Failed to generate serpentine pattern: {str(e)}") from e

    async def generate_spiral(
        self,
        origin: List[float],
        diameter: float,
        pitch: float,
        speed: float,
        z_height: float,
        acceleration: float,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate spiral pattern."""
        try:
            # Validate inputs
            await self._validate_pattern_params({
                "origin": origin,
                "diameter": diameter,
                "pitch": pitch,
                "speed": speed,
                "z_height": z_height,
                "acceleration": acceleration
            })

            # Generate pattern metadata
            pattern = {
                "pattern": {
                    "metadata": {
                        "name": name or f"Spiral_{diameter}mm_{speed}mms",
                        "version": "1.0",
                        "created": datetime.now().isoformat(),
                        "description": f"Generated spiral pattern with {diameter}mm diameter"
                    },
                    "type": "spiral",
                    "params": {
                        "origin": origin,
                        "diameter": diameter,
                        "pitch": pitch,
                        "speed": speed,
                        "z_height": z_height,
                        "acceleration": acceleration
                    }
                }
            }

            return pattern

        except Exception as e:
            logger.error(f"Error generating spiral pattern: {e}")
            raise PatternError(f"Failed to generate spiral pattern: {str(e)}") from e

    async def generate_linear(
        self,
        start: List[float],
        end: List[float],
        speed: float,
        z_height: float,
        acceleration: float,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate linear pattern."""
        try:
            # Validate inputs
            self._validate_pattern_params({
                "start": start,
                "end": end,
                "speed": speed,
                "z_height": z_height,
                "acceleration": acceleration
            })
            
            # Generate pattern metadata
            pattern = {
                "pattern": {
                    "metadata": {
                        "name": name or f"Linear_{speed}mms",
                        "version": "1.0",
                        "created": datetime.now().isoformat(),
                        "description": "Generated linear pattern"
                    },
                    "type": "linear",
                    "params": {
                        "start": start,
                        "end": end,
                        "speed": speed,
                        "z_height": z_height,
                        "acceleration": acceleration
                    }
                }
            }
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error generating linear pattern: {e}")
            raise PatternError(f"Failed to generate linear pattern: {str(e)}") from e

    async def _validate_pattern_params(self, params: Dict[str, Any]) -> None:
        """Validate pattern parameters."""
        try:
            # Get hardware limits from config
            hardware_config = self._config_manager.get_config("hardware")
            motion_limits = hardware_config["motion"]["limits"]

            # Validate position limits
            if "origin" in params:
                x, y = params["origin"]
                if not (motion_limits["x"]["min"] <= x <= motion_limits["x"]["max"]):
                    raise PatternError(f"X origin {x} outside limits")
                if not (motion_limits["y"]["min"] <= y <= motion_limits["y"]["max"]):
                    raise PatternError(f"Y origin {y} outside limits")

            # Validate z height
            if "z_height" in params:
                z = params["z_height"]
                if not (motion_limits["z"]["min"] <= z <= motion_limits["z"]["max"]):
                    raise PatternError(f"Z height {z} outside limits")

            # Validate motion parameters
            if "speed" in params:
                speed = params["speed"]
                if not (0 < speed <= motion_limits["velocity"]["max"]):
                    raise PatternError(f"Speed {speed} outside limits")

            if "acceleration" in params:
                accel = params["acceleration"]
                if not (0 < accel <= motion_limits["acceleration"]["max"]):
                    raise PatternError(f"Acceleration {accel} outside limits")

            # Validate pattern-specific parameters
            if "length" in params:
                length = params["length"]
                if length <= 0:
                    raise PatternError(f"Invalid length {length}")

            if "spacing" in params:
                spacing = params["spacing"]
                if spacing <= 0:
                    raise PatternError(f"Invalid spacing {spacing}")

            if "diameter" in params:
                diameter = params["diameter"]
                if diameter <= 0:
                    raise PatternError(f"Invalid diameter {diameter}")

            if "pitch" in params:
                pitch = params["pitch"]
                if pitch <= 0:
                    raise PatternError(f"Invalid pitch {pitch}")

        except Exception as e:
            logger.error(f"Pattern validation failed: {e}")
            # Publish validation error
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": "Pattern validation failed",
                    "details": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise PatternError(f"Pattern validation failed: {str(e)}") from e

    async def _validate_sprayable_area(self, pattern_data: Dict[str, Any]) -> None:
        """Validate pattern stays within sprayable area."""
        try:
            # Get sprayable area limits from hardware config
            hardware_config = self._config_manager.get_config("hardware")
            sprayable_area = hardware_config["physical"]["substrate_holder"]["dimensions"]["sprayable"]
            
            # Get pattern bounds based on type
            pattern_type = pattern_data["pattern"]["type"]
            params = pattern_data["pattern"]["params"]
            
            if pattern_type == "serpentine":
                origin = params["origin"]
                length = params["length"]
                spacing = params["spacing"]
                
                # Calculate pattern bounds
                x_min = origin[0]
                x_max = origin[0] + length
                y_min = origin[1]
                y_max = origin[1] + spacing
                
            elif pattern_type == "spiral":
                origin = params["origin"]
                diameter = params["diameter"]
                
                # Calculate pattern bounds
                x_min = origin[0] - (diameter/2)
                x_max = origin[0] + (diameter/2)
                y_min = origin[1] - (diameter/2)
                y_max = origin[1] + (diameter/2)
                
            elif pattern_type == "linear":
                start = params["start"]
                end = params["end"]
                
                # Calculate pattern bounds
                x_min = min(start[0], end[0])
                x_max = max(start[0], end[0])
                y_min = min(start[1], end[1])
                y_max = max(start[1], end[1])
                
            # Validate bounds against sprayable area
            if (x_min < 0 or
                x_max > sprayable_area["width"] or
                y_min < 0 or
                y_max > sprayable_area["height"]):
                error_msg = (
                    f"Pattern exceeds sprayable area bounds: "
                    f"[0, {sprayable_area['width']}] x "
                    f"[0, {sprayable_area['height']}]"
                )
                # Publish error
                await self._message_broker.publish(
                    "patterns/error",
                    {
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                raise PatternError(error_msg)
                
        except Exception as e:
            logger.error(f"Error validating sprayable area: {e}")
            # Publish error
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": f"Failed to validate sprayable area: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise PatternError(f"Failed to validate sprayable area: {str(e)}") from e

    async def save_pattern(self, pattern: Dict[str, Any], filename: str) -> None:
        """Save pattern to file."""
        try:
            # Validate pattern first
            pattern_type = pattern["pattern"]["type"]
            await self._validate_pattern_params(pattern["pattern"]["params"])
            await self._validate_sprayable_area(pattern)
            
            # Save to appropriate directory
            if pattern_type == "custom":
                file_path = self._custom_path / filename
            else:
                file_path = self._pattern_path / pattern_type / filename
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save pattern
            with open(file_path, 'w') as f:
                yaml.safe_dump(pattern, f, sort_keys=False)
            
            # Publish saved event
            await self._message_broker.publish(
                "patterns/saved",
                {
                    "filename": filename,
                    "type": pattern_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": f"Failed to save pattern: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise PatternError(f"Failed to save pattern: {str(e)}") from e