"""Process validation component."""
from typing import Dict, Any, Optional
import logging

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ProcessValidator:
    """Validates process parameters and configurations."""
    
    def __init__(self, message_broker: MessageBroker):
        self._message_broker = message_broker
        self._config_manager = ConfigManager()
        
        # Subscribe to validation requests
        self._message_broker.subscribe("parameters/validate", self._handle_validation_request)
        
    async def _handle_validation_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter validation requests."""
        try:
            validation_result = self.validate_parameters(data.get("parameters", {}))
            await self._message_broker.publish("parameters/validate/result", validation_result)
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            await self._message_broker.publish("parameters/validate/result", {
                "valid": False,
                "error": str(e)
            })

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate process parameters against configuration limits."""
        try:
            process_config = self._config_manager.get_config("process")
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Validate motion parameters
            if "motion" in parameters:
                self._validate_motion_params(parameters["motion"], process_config, validation_results)
                
            # Validate process parameters
            if "process" in parameters:
                self._validate_process_params(parameters["process"], process_config, validation_results)
            
            validation_results["valid"] = len(validation_results["errors"]) == 0
            return validation_results
            
        except Exception as e:
            logger.error(f"Parameter validation error: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }

    def _validate_motion_params(self, motion_params: Dict[str, Any], 
                              config: Dict[str, Any], 
                              results: Dict[str, Any]) -> None:
        """Validate motion-related parameters."""
        try:
            # Get motion limits from config
            limits = config.get('limits', {}).get('motion', {})
            
            # Validate axis
            axis = motion_params.get('axis')
            if axis not in ['x', 'y', 'z']:
                results["errors"].append(f"Invalid axis: {axis}")
                
            # Validate distance
            distance = motion_params.get('distance')
            if distance is not None:
                axis_limits = limits.get(axis, {})
                current_pos = motion_params.get('current_position', 0)
                target_pos = current_pos + distance
                
                if target_pos < axis_limits.get('min', float('-inf')):
                    results["errors"].append(
                        f"{axis} target position {target_pos} below minimum limit "
                        f"{axis_limits.get('min')}"
                    )
                if target_pos > axis_limits.get('max', float('inf')):
                    results["errors"].append(
                        f"{axis} target position {target_pos} above maximum limit "
                        f"{axis_limits.get('max')}"
                    )
                    
            # Validate velocity
            velocity = motion_params.get('velocity')
            if velocity is not None:
                vel_limits = limits.get('velocity', {})
                if velocity < vel_limits.get('min', 0):
                    results["errors"].append(f"Velocity below minimum limit")
                if velocity > vel_limits.get('max', float('inf')):
                    results["errors"].append(f"Velocity above maximum limit")
                    
            # Validate acceleration/deceleration
            for param in ['acceleration', 'deceleration']:
                value = motion_params.get(param)
                if value is not None:
                    acc_limits = limits.get(param, {})
                    if value < acc_limits.get('min', 0):
                        results["errors"].append(f"{param} below minimum limit")
                    if value > acc_limits.get('max', float('inf')):
                        results["errors"].append(f"{param} above maximum limit")
                        
        except Exception as e:
            logger.error(f"Error validating motion parameters: {e}")
            results["errors"].append(f"Validation error: {str(e)}")

    def _validate_process_params(self, process_params: Dict[str, Any],
                               config: Dict[str, Any],
                               results: Dict[str, Any]) -> None:
        """Validate process-related parameters."""
        limits = config.get("limits", {}).get("process", {})
        
        for param, value in process_params.items():
            param_limits = limits.get(param, {})
            if param_limits:
                if value < param_limits.get("min", float("-inf")):
                    results["errors"].append(f"{param} below minimum limit")
                if value > param_limits.get("max", float("inf")):
                    results["errors"].append(f"{param} above maximum limit")