"""Parameter management service."""

from typing import Dict, Any, List
from pathlib import Path
import yaml
from loguru import logger

from ...base import BaseService
from ...config import ConfigService
from ..exceptions import ProcessError


class ParameterService(BaseService):
    """Service for managing process parameters."""

    def __init__(self, config_service: ConfigService):
        """Initialize parameter service.
        
        Args:
            config_service: Configuration service
        """
        super().__init__(service_name="parameter", config_service=config_service)
        self._config: Dict[str, Any] = {}
        self._parameter_sets: Dict[str, Dict[str, Any]] = {}

    async def _start(self) -> None:
        """Initialize parameter service."""
        try:
            # Load configuration
            config = await self._config_service.get_config("process")
            self._config = config.get("process", {})
            
            # Load parameter sets
            await self._load_parameter_sets()
            
            logger.info("Parameter service started")
            
        except Exception as e:
            error_context = {
                "source": "parameter_service",
                "error": str(e)
            }
            logger.error("Failed to start parameter service", extra=error_context)
            raise ProcessError("Failed to start parameter service", error_context)

    async def get_parameter_set(self, set_id: str) -> Dict[str, Any]:
        """Get parameter set by ID.
        
        Args:
            set_id: Parameter set ID
            
        Returns:
            Parameter set data
            
        Raises:
            ProcessError: If parameter set not found
        """
        if set_id not in self._parameter_sets:
            raise ProcessError(f"Parameter set not found: {set_id}")
            
        return self._parameter_sets[set_id]

    async def list_parameter_sets(self) -> List[Dict[str, Any]]:
        """List available parameter sets.
        
        Returns:
            List of parameter sets with metadata
        """
        return [
            {
                "id": set_id,
                "name": params.get("name", set_id),
                "description": params.get("description", ""),
                "metadata": params.get("metadata", {})
            }
            for set_id, params in self._parameter_sets.items()
        ]

    async def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate parameter values.
        
        Args:
            parameters: Parameter values to validate
            
        Raises:
            ProcessError: If parameters are invalid
        """
        try:
            schema = self._config.get("parameters", {}).get("schema", {})
            
            # Basic schema validation
            for param_name, param_value in parameters.items():
                if param_name not in schema:
                    raise ProcessError(f"Unknown parameter: {param_name}")
                    
                param_schema = schema[param_name]
                param_type = param_schema.get("type")
                
                # Type validation
                if param_type == "number":
                    if not isinstance(param_value, (int, float)):
                        raise ProcessError(f"Invalid type for {param_name}: expected number")
                        
                    # Range validation
                    min_val = param_schema.get("min")
                    max_val = param_schema.get("max")
                    
                    if min_val is not None and param_value < min_val:
                        raise ProcessError(f"Parameter {param_name} below minimum: {min_val}")
                    if max_val is not None and param_value > max_val:
                        raise ProcessError(f"Parameter {param_name} above maximum: {max_val}")
                        
                elif param_type == "string":
                    if not isinstance(param_value, str):
                        raise ProcessError(f"Invalid type for {param_name}: expected string")
                        
                    # Enum validation
                    allowed_values = param_schema.get("enum")
                    if allowed_values and param_value not in allowed_values:
                        raise ProcessError(f"Invalid value for {param_name}: must be one of {allowed_values}")
                        
                elif param_type == "boolean":
                    if not isinstance(param_value, bool):
                        raise ProcessError(f"Invalid type for {param_name}: expected boolean")

        except ProcessError:
            raise
        except Exception as e:
            raise ProcessError("Parameter validation failed", {"error": str(e)})

    async def _load_parameter_sets(self) -> None:
        """Load parameter sets from files."""
        try:
            param_path = Path(self._config["paths"]["data"]["parameters"]["root"])
            
            for file_path in param_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.safe_load(f)
                        self._parameter_sets[file_path.stem] = data
                except Exception as e:
                    logger.warning(f"Error loading parameter file {file_path}: {e}")
                    
        except Exception as e:
            raise ProcessError("Failed to load parameter sets", {"error": str(e)})
