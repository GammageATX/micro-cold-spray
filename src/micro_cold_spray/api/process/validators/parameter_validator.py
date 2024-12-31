"""Parameter validation for process API."""

from typing import Dict, Any, List, Tuple
from loguru import logger

from micro_cold_spray.api.process.models.process_models import ParameterSet


def validate_parameter(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate parameter data against hardware capabilities.
    
    Args:
        data: Parameter data to validate
        
    Returns:
        (is_valid, errors): Validation result and error messages
    """
    errors = []
    
    if "process" not in data:
        errors.append("Missing 'process' root key")
        return False, errors
        
    process = data["process"]
    
    # Gas flow limits
    if "main_gas" in process:
        main_gas = process["main_gas"]
        if not 0 <= main_gas <= 100:  # MFC limits
            errors.append("Main gas flow must be between 0-100 SLPM")
            
    if "feeder_gas" in process:
        feeder_gas = process["feeder_gas"]
        if not 0 <= feeder_gas <= 50:  # Feeder MFC limits
            errors.append("Feeder gas flow must be between 0-50 SLPM")
            
    # Frequency limits
    if "frequency" in process:
        freq = process["frequency"]
        if not 0 <= freq <= 1000:  # Hardware frequency limits
            errors.append("Frequency must be between 0-1000 Hz")
            
    # Deagglomerator limits
    if "deagglomerator_speed" in process:
        speed = process["deagglomerator_speed"]
        if not 0 <= speed <= 100:  # Motor speed limits
            errors.append("Deagglomerator speed must be between 0-100%")
            
    # Additional hardware-specific validations...
    
    return len(errors) == 0, errors
