"""Sequence validation for process API."""

from typing import Dict, Any, List, Tuple
from loguru import logger

from micro_cold_spray.api.process.models.process_models import (
    Sequence, SequenceStep, SequenceMetadata
)


def validate_sequence(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate sequence data against system capabilities.
    
    Args:
        data: Sequence data to validate
        
    Returns:
        (is_valid, errors): Validation result and error messages
    """
    errors = []
    
    if "sequence" not in data:
        errors.append("Missing 'sequence' root key")
        return False, errors
        
    sequence = data["sequence"]
    
    # Validate steps
    if "steps" in sequence:
        steps = sequence["steps"]
        
        # Check step ordering
        current_state = "idle"
        for i, step in enumerate(steps):
            # Validate state transitions
            if step["action_group"] == "spray":
                if current_state != "ready":
                    errors.append(f"Step {i+1}: Cannot spray unless system is ready")
                    
            elif step["action_group"] == "initialize":
                if current_state != "idle":
                    errors.append(f"Step {i+1}: Can only initialize from idle state")
                    
            # Update state based on action
            if step["action_group"] == "initialize":
                current_state = "ready"
            elif step["action_group"] == "shutdown":
                current_state = "idle"
                
            # Validate step parameters
            if "pattern" in step and "parameters" not in step:
                errors.append(f"Step {i+1}: Pattern requires parameters")
                
            if "parameters" in step and "pattern" not in step:
                errors.append(f"Step {i+1}: Parameters require pattern")
    
    return len(errors) == 0, errors
