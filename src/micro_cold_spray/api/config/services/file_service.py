"""File service for managing configuration files."""

import os
from typing import List, Dict, Any
from loguru import logger

from micro_cold_spray.api.base import create_error
from micro_cold_spray.api.config.services.base_config_service import BaseConfigService


class FileService(BaseConfigService):
    """Service for managing configuration files."""
    
    def __init__(self, base_path: str = None):
        """Initialize file service.
        
        Args:
            base_path: Base path for configuration files
        """
        super().__init__("file")
        self.base_path = base_path or os.getcwd()
        
    async def _start(self):
        """Start file service."""
        # Create base path if it doesn't exist
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            logger.info(f"Created config directory: {self.base_path}")
    
    async def _stop(self):
        """Stop file service."""
        pass
    
    def list_configs(self) -> List[str]:
        """List available configuration files.
        
        Returns:
            List[str]: List of configuration filenames
        """
        if not self.is_running:
            raise create_error(
                status_code=503,
                message="File service not running"
            )
        
        try:
            # Get all YAML files in base path
            files = []
            for filename in os.listdir(self.base_path):
                if filename.endswith(('.yaml', '.yml')):
                    files.append(filename)
            return files
            
        except Exception as e:
            logger.error(f"Failed to list configs: {e}")
            raise create_error(
                status_code=500,
                message=f"Failed to list configs: {str(e)}"
            )
    
    def read(self, filename: str) -> Dict[str, Any]:
        """Read configuration file.
        
        Args:
            filename: Name of file to read
            
        Returns:
            Dict[str, Any]: Configuration data
        """
        if not self.is_running:
            raise create_error(
                status_code=503,
                message="File service not running"
            )
        
        try:
            # Get full path
            filepath = os.path.join(self.base_path, filename)
            
            # Check file exists
            if not os.path.exists(filepath):
                raise create_error(
                    status_code=404,
                    message=f"File not found: {filename}"
                )
            
            # Read file
            with open(filepath, 'r') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to read config {filename}: {e}")
            raise create_error(
                status_code=500,
                message=f"Failed to read config {filename}: {str(e)}"
            )
    
    def write(self, filename: str, data: str):
        """Write configuration file.
        
        Args:
            filename: Name of file to write
            data: Configuration data to write
        """
        if not self.is_running:
            raise create_error(
                status_code=503,
                message="File service not running"
            )
        
        try:
            # Get full path
            filepath = os.path.join(self.base_path, filename)
            
            # Write file
            with open(filepath, 'w') as f:
                f.write(data)
                
        except Exception as e:
            logger.error(f"Failed to write config {filename}: {e}")
            raise create_error(
                status_code=500,
                message=f"Failed to write config {filename}: {str(e)}"
            )
    
    def delete(self, filename: str):
        """Delete configuration file.
        
        Args:
            filename: Name of file to delete
        """
        if not self.is_running:
            raise create_error(
                status_code=503,
                message="File service not running"
            )
        
        try:
            # Get full path
            filepath = os.path.join(self.base_path, filename)
            
            # Check file exists
            if not os.path.exists(filepath):
                raise create_error(
                    status_code=404,
                    message=f"File not found: {filename}"
                )
            
            # Delete file
            os.remove(filepath)
            
        except Exception as e:
            logger.error(f"Failed to delete config {filename}: {e}")
            raise create_error(
                status_code=500,
                message=f"Failed to delete config {filename}: {str(e)}"
            )
    
    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status
        """
        status = await super().health()
        
        try:
            # Check if base path exists and is writable
            path_exists = os.path.exists(self.base_path)
            path_writable = os.access(self.base_path, os.W_OK)
            
            status.update({
                "details": {
                    "base_path": self.base_path,
                    "path_exists": path_exists,
                    "path_writable": path_writable,
                    "config_count": len(self.list_configs()) if self.is_running else 0
                }
            })
            
        except (OSError, PermissionError) as e:
            logger.error(f"Health check failed: {e}")
            status.update({
                "is_healthy": False,
                "details": {
                    "error": str(e)
                }
            })
            
        return status
