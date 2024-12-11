"""Pattern management service."""

from typing import Dict, Any
from pathlib import Path
import yaml
from loguru import logger

from ...base import BaseService
from ...config import ConfigService
from ...messaging import MessagingService
from ..exceptions import ProcessError


class PatternService(BaseService):
    """Service for managing pattern operations."""

    def __init__(
        self,
        config_service: ConfigService,
        message_broker: MessagingService
    ):
        """Initialize pattern service.
        
        Args:
            config_service: Configuration service
            message_broker: Message broker service
        """
        super().__init__(service_name="pattern", config_service=config_service)
        self._message_broker = message_broker
        self._config: Dict[str, Any] = {}

    async def _start(self) -> None:
        """Initialize pattern service."""
        try:
            # Load configuration
            config = await self._config_service.get_config("process")
            self._config = config.get("process", {})
            
            logger.info("Pattern service started")
            
        except Exception as e:
            error_context = {
                "source": "pattern_service",
                "error": str(e)
            }
            logger.error("Failed to start pattern service", extra=error_context)
            raise ProcessError("Failed to start pattern service", error_context)

    async def generate_pattern(self, pattern_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate new pattern.
        
        Args:
            pattern_type: Type of pattern to generate
            parameters: Pattern generation parameters
            
        Returns:
            Generated pattern data
            
        Raises:
            ProcessError: If pattern cannot be generated
        """
        try:
            # Validate pattern type
            if pattern_type not in self._config.get("patterns", {}).get("types", []):
                raise ProcessError(f"Invalid pattern type: {pattern_type}")

            # Generate pattern via messaging API
            response = await self._message_broker.request(
                "pattern/generate",
                {
                    "type": pattern_type,
                    "parameters": parameters
                }
            )

            if response.get("status") != "success":
                raise ProcessError(
                    "Pattern generation failed",
                    {"error": response.get("error")}
                )

            return response.get("pattern", {})

        except Exception as e:
            error_context = {
                "type": pattern_type,
                "parameters": parameters,
                "error": str(e)
            }
            logger.error("Failed to generate pattern", extra=error_context)
            raise ProcessError("Failed to generate pattern", error_context)

    async def validate_pattern(self, pattern_id: str) -> None:
        """Validate pattern.
        
        Args:
            pattern_id: ID of pattern to validate
            
        Raises:
            ProcessError: If pattern validation fails
        """
        try:
            # Load pattern data
            pattern_data = await self._load_pattern_file(pattern_id)
            
            # Validate via messaging API
            response = await self._message_broker.request(
                "pattern/validate",
                pattern_data
            )

            if response.get("status") != "success":
                raise ProcessError(
                    "Pattern validation failed",
                    {"error": response.get("error")}
                )

        except Exception as e:
            error_context = {
                "pattern_id": pattern_id,
                "error": str(e)
            }
            logger.error("Failed to validate pattern", extra=error_context)
            raise ProcessError("Failed to validate pattern", error_context)

    async def list_pattern_files(self) -> Dict[str, Any]:
        """List available pattern files.
        
        Returns:
            Dict containing pattern files and their metadata
            
        Raises:
            ProcessError: If files cannot be listed
        """
        try:
            pattern_path = Path(self._config["paths"]["data"]["patterns"]["root"])
            files = []
            
            for file_path in pattern_path.glob("*.yaml"):
                try:
                    with open(file_path) as f:
                        data = yaml.safe_load(f)
                        files.append({
                            "name": file_path.stem,
                            "path": str(file_path),
                            "type": data.get("type"),
                            "metadata": data.get("metadata", {})
                        })
                except Exception as e:
                    logger.warning(f"Error loading pattern file {file_path}: {e}")
                    
            return {"files": files}
            
        except Exception as e:
            raise ProcessError("Failed to list pattern files", {"error": str(e)})

    async def _load_pattern_file(self, pattern_id: str) -> Dict[str, Any]:
        """Load pattern file.
        
        Args:
            pattern_id: ID of pattern to load
            
        Returns:
            Pattern data
            
        Raises:
            ProcessError: If pattern file cannot be loaded
        """
        try:
            pattern_path = Path(self._config["paths"]["data"]["patterns"]["root"])
            file_path = pattern_path / f"{pattern_id}.yaml"
            
            if not file_path.exists():
                raise ProcessError(f"Pattern file not found: {pattern_id}")
            
            with open(file_path) as f:
                return yaml.safe_load(f)
                
        except Exception as e:
            raise ProcessError(f"Failed to load pattern file: {e}")
