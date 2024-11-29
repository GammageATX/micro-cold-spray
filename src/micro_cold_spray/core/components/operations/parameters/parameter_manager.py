from typing import Dict, Any, Optional, List
from loguru import logger
import asyncio
from datetime import datetime
from pathlib import Path
import yaml

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator
from ....exceptions import OperationError, ParameterError

class ParameterManager:
    """Manages spray parameter files and nozzle configurations."""
    
    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        parameter_path: Path = Path("data/parameters/library"),
        nozzle_path: Path = Path("data/parameters/library/nozzles")
    ) -> None:
        """Initialize parameter manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._parameter_path = parameter_path
        self._nozzle_path = nozzle_path
        self._loaded_parameters: Optional[Dict[str, Any]] = None
        self._active_nozzle: Optional[Dict[str, Any]] = None
        
        logger.info("Parameter manager initialized")

    async def initialize(self) -> None:
        """Initialize parameter manager."""
        try:
            if self._is_initialized:
                return
                
            # Load parameters from config
            parameters_config = self._config_manager.get_config('parameters')
            self._parameters = parameters_config.get('parameters', {})
            
            # Subscribe to parameter-related messages
            await self._message_broker.subscribe(
                "parameter/update",
                self._handle_parameter_update
            )
            await self._message_broker.subscribe(
                "parameters/load",
                self._handle_load_request
            )
            await self._message_broker.subscribe(
                "parameters/save",
                self._handle_save_request
            )
            
            # Create directories if they don't exist
            self._parameter_path.mkdir(parents=True, exist_ok=True)
            self._nozzle_path.mkdir(parents=True, exist_ok=True)
            
            self._is_initialized = True
            logger.info("Parameter manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize parameter manager")
            raise OperationError(f"Parameter manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown parameter manager."""
        try:
            # Save parameters to config if needed
            await self._config_manager.update_config('parameters', {'parameters': self._parameters})
            self._is_initialized = False
            logger.info("Parameter manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during parameter manager shutdown")
            raise OperationError(f"Parameter manager shutdown failed: {str(e)}") from e

    async def _handle_parameter_update(self, data: Dict[str, Any]) -> None:
        """Handle parameter update messages."""
        try:
            command = data.get('command')
            if not command:
                raise ValueError("Missing command in parameter update")
                
            if command == 'update':
                await self.update_parameter_set(
                    data['set_name'],
                    data['updates']
                )
            elif command == 'create':
                await self.create_parameter_set(
                    data['set_name'],
                    data['parameters']
                )
                
        except Exception as e:
            logger.error(f"Error handling parameter update: {e}")
            await self._message_broker.publish(
                "parameter/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def get_parameter_set(self, set_name: str) -> Dict[str, Any]:
        """Get a parameter set by name."""
        try:
            if set_name not in self._parameters:
                raise ValueError(f"Parameter set not found: {set_name}")
                
            # Update access state through TagManager
            await self._tag_manager.set_tag(
                "parameters.access",
                {
                    "set_name": set_name,
                    "action": "read",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return self._parameters[set_name].copy()
            
        except Exception as e:
            logger.error(f"Error getting parameter set {set_name}: {e}")
            raise OperationError(f"Failed to get parameter set: {str(e)}") from e

    async def update_parameter_set(self, set_name: str, updates: Dict[str, Any]) -> None:
        """Update a parameter set."""
        try:
            if set_name not in self._parameters:
                raise ValueError(f"Parameter set not found: {set_name}")
                
            # Validate updates
            await self._validator.validate_parameters(set_name, updates)
            
            # Update parameters
            self._parameters[set_name].update(updates)
            
            # Update through config manager
            await self._config_manager.update_config(
                'parameters',
                {'parameters': {set_name: self._parameters[set_name]}}
            )
            
            # Update state through TagManager
            await self._tag_manager.set_tag(
                "parameters.state",
                {
                    "set_name": set_name,
                    "status": "updated",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Notify system through MessageBroker
            await self._message_broker.publish(
                "parameters/updated",
                {
                    "set_name": set_name,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating parameter set {set_name}: {e}")
            raise OperationError(f"Failed to update parameter set: {str(e)}") from e

    def list_parameter_sets(self) -> Dict[str, Dict[str, Any]]:
        """Get all parameter sets."""
        return self._parameters.copy()

    def get_available_nozzles(self) -> List[Dict[str, Any]]:
        """Get list of available nozzle configurations."""
        try:
            nozzles = []
            for file in self._nozzle_path.glob("*.yaml"):
                with open(file, 'r') as f:
                    nozzle = yaml.safe_load(f)
                    nozzles.append(nozzle["nozzle"])
            return nozzles
            
        except Exception as e:
            logger.error(f"Error loading nozzle configurations: {e}")
            raise ParameterError(f"Failed to load nozzle configurations: {str(e)}") from e

    def get_available_parameters(self) -> List[Dict[str, Any]]:
        """Get list of available parameter files."""
        try:
            parameters = []
            for file in self._parameter_path.glob("*.yaml"):
                if file.stem != "nozzles":  # Skip nozzle directory
                    with open(file, 'r') as f:
                        param = yaml.safe_load(f)
                        parameters.append({
                            "name": param["process"]["metadata"]["name"],
                            "file": file.name,
                            "nozzle": param["process"]["nozzle"]["type"]
                        })
            return parameters
            
        except Exception as e:
            logger.error(f"Error loading parameter files: {e}")
            raise ParameterError(f"Failed to load parameter files: {str(e)}") from e

    async def load_parameters(self, filename: str) -> Dict[str, Any]:
        """Load parameter file."""
        try:
            file_path = self._parameter_path / filename
            if not file_path.exists():
                raise ParameterError(f"Parameter file not found: {filename}")
                
            with open(file_path, 'r') as f:
                parameters = yaml.safe_load(f)
                
            # Load associated nozzle config
            nozzle_type = parameters["process"]["nozzle"]["type"]
            nozzle_file = self._nozzle_path / f"{nozzle_type.lower()}.yaml"
            
            with open(nozzle_file, 'r') as f:
                nozzle = yaml.safe_load(f)
                
            # Store loaded configs
            self._loaded_parameters = parameters
            self._active_nozzle = nozzle
            
            # Publish parameter loaded event
            await self._message_broker.publish(
                "parameters/loaded",
                {
                    "parameters": parameters,
                    "nozzle": nozzle,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error loading parameters: {e}")
            raise ParameterError(f"Failed to load parameters: {str(e)}") from e

    async def save_parameters(
        self,
        parameters: Dict[str, Any],
        filename: Optional[str] = None
    ) -> None:
        """Save parameter file."""
        try:
            if filename is None:
                # Generate filename from metadata
                name = parameters["process"]["metadata"]["name"]
                filename = f"{name.lower().replace(' ', '_')}.yaml"
                
            file_path = self._parameter_path / filename
            
            with open(file_path, 'w') as f:
                yaml.safe_dump(parameters, f, sort_keys=False)
                
            logger.info(f"Saved parameters to {filename}")
            
            # Publish parameter saved event
            await self._message_broker.publish(
                "parameters/saved",
                {
                    "filename": filename,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error saving parameters: {e}")
            raise ParameterError(f"Failed to save parameters: {str(e)}") from e

    async def _handle_load_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter load request."""
        try:
            filename = data["filename"]
            await self.load_parameters(filename)
            
        except Exception as e:
            logger.error(f"Error handling load request: {e}")
            await self._message_broker.publish(
                "parameters/error",
                {
                    "error": str(e),
                    "context": "load_request",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_save_request(self, data: Dict[str, Any]) -> None:
        """Handle parameter save request."""
        try:
            parameters = data["parameters"]
            filename = data.get("filename")
            await self.save_parameters(parameters, filename)
            
        except Exception as e:
            logger.error(f"Error handling save request: {e}")
            await self._message_broker.publish(
                "parameters/error",
                {
                    "error": str(e),
                    "context": "save_request",
                    "timestamp": datetime.now().isoformat()
                }
            )