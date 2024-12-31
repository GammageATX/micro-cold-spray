"""Pattern validation for process API."""

from typing import Dict, Any, List, Tuple
from loguru import logger

from micro_cold_spray.api.process.models.process_models import ProcessPattern


def validate_pattern(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate pattern data against motion system capabilities.
    
    Args:
        data: Pattern data to validate
        
    Returns:
        (is_valid, errors): Validation result and error messages
    """
    errors = []
    
    if "pattern" not in data:
        errors.append("Missing 'pattern' root key")
        return False, errors
        
    pattern = data["pattern"]
    
    # Motion limits
    if "params" in pattern:
        params = pattern["params"]
        
        # Workspace limits
        if "width" in params:
            width = params["width"]
            if not 0 <= width <= 500:  # Machine X travel
                errors.append("Pattern width must be between 0-500mm")
                
        if "height" in params:
            height = params["height"]
            if not 0 <= height <= 500:  # Machine Y travel
                errors.append("Pattern height must be between 0-500mm")
                
        if "z_height" in params:
            z_height = params["z_height"]
            if not 0 <= z_height <= 100:  # Machine Z travel
                errors.append("Z height must be between 0-100mm")
        
        # Velocity limits
        if "velocity" in params:
            velocity = params["velocity"]
            if not 0 < velocity <= 500:  # Max speed
                errors.append("Velocity must be between 0-500 mm/s")
                
        # Line spacing limits
        if "line_spacing" in params:
            spacing = params["line_spacing"]
            if not 0.1 <= spacing <= 50:  # Min/max spacing
                errors.append("Line spacing must be between 0.1-50mm")
    
    return len(errors) == 0, errors
