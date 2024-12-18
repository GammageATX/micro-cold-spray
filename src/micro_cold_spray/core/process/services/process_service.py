"""Process service implementation."""

from typing import Dict, Any, Optional
from loguru import logger

from micro_cold_spray.core.base import BaseService
from micro_cold_spray.core.errors import ProcessError, ValidationError
from micro_cold_spray.infrastructure.config import settings, get_config, validate_config


class ProcessService(BaseService):
    """Service for managing spray processes."""

    def __init__(self):
        """Initialize process service."""
        super().__init__(service_name="process")
        
        # Get validation settings
        self.chamber_pressure_max = settings.process.validation.chamber_pressure_max
        self.min_feeder_flow = settings.process.validation.min_feeder_flow
        
        # Get gas settings
        self.gas_types = {gas["name"]: gas for gas in settings.gas.types}
        
        # Get hardware sets
        self.hardware_sets = settings.hardware.sets
    
    async def load_process(self, name: str) -> Dict[str, Any]:
        """Load a process configuration.
        
        Args:
            name: Name of the process configuration
            
        Returns:
            Process configuration data
            
        Raises:
            ProcessError: If process configuration is not found or invalid
        """
        try:
            # Get process config
            process = get_config("process", name)
            if not process:
                raise ProcessError(f"Process configuration '{name}' not found")
            
            # Validate process config
            if not validate_config("process", process):
                raise ValidationError(f"Invalid process configuration: {name}")
            
            return process
            
        except Exception as e:
            logger.error(f"Failed to load process {name}: {e}")
            raise ProcessError(f"Failed to load process: {str(e)}")
    
    async def validate_parameters(self, process: Dict[str, Any]) -> None:
        """Validate process parameters.
        
        Args:
            process: Process configuration to validate
            
        Raises:
            ValidationError: If parameters are invalid
        """
        try:
            # Validate gas parameters
            gas_type = process["gas"]["type"]
            if gas_type not in self.gas_types:
                raise ValidationError(f"Invalid gas type: {gas_type}")
            
            gas_config = self.gas_types[gas_type]
            main_flow = process["gas"]["main_flow"]
            feeder_flow = process["gas"]["feeder_flow"]
            
            if not (gas_config["flow_control"]["main"]["flow_min"] <= main_flow <= gas_config["flow_control"]["main"]["flow_max"]):
                raise ValidationError(f"Main flow {main_flow} outside valid range")
                
            if not (gas_config["flow_control"]["feeder"]["flow_min"] <= feeder_flow <= gas_config["flow_control"]["feeder"]["flow_max"]):
                raise ValidationError(f"Feeder flow {feeder_flow} outside valid range")
            
            # Validate hardware set
            hardware_set = process["hardware"]["set"]
            if hardware_set not in self.hardware_sets:
                raise ValidationError(f"Invalid hardware set: {hardware_set}")
            
            # Add more validation as needed...
            
        except KeyError as e:
            raise ValidationError(f"Missing required parameter: {e}")
        except Exception as e:
            raise ValidationError(f"Parameter validation failed: {str(e)}")
    
    async def apply_parameters(self, process: Dict[str, Any]) -> None:
        """Apply process parameters to hardware.
        
        Args:
            process: Process configuration to apply
            
        Raises:
            ProcessError: If parameters cannot be applied
        """
        try:
            # Validate parameters first
            await self.validate_parameters(process)
            
            # Apply hardware set
            hardware_set = process["hardware"]["set"]
            await self._apply_hardware_set(self.hardware_sets[hardware_set])
            
            # Apply gas parameters
            await self._apply_gas_parameters(process["gas"])
            
            # Apply powder feed parameters
            await self._apply_powder_feed(process["powder_feed"])
            
            # Apply motion parameters
            await self._apply_motion_parameters(process["motion"])
            
        except Exception as e:
            logger.error(f"Failed to apply parameters: {e}")
            raise ProcessError(f"Failed to apply parameters: {str(e)}")
    
    async def _apply_hardware_set(self, hardware: Dict[str, Any]) -> None:
        """Apply hardware set configuration."""
        # Implementation depends on your hardware control system
        pass
    
    async def _apply_gas_parameters(self, gas: Dict[str, Any]) -> None:
        """Apply gas flow parameters."""
        # Implementation depends on your gas control system
        pass
    
    async def _apply_powder_feed(self, powder: Dict[str, Any]) -> None:
        """Apply powder feed parameters."""
        # Implementation depends on your powder feed system
        pass
    
    async def _apply_motion_parameters(self, motion: Dict[str, Any]) -> None:
        """Apply motion parameters."""
        # Implementation depends on your motion control system
        pass
