"""File service for managing configuration files."""

import os
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger

from micro_cold_spray.utils.errors import create_error


class FileService:
    """Service for managing configuration files."""
    
    def __init__(self, base_path: str = None):
        """Initialize file service.
        
        Args:
            base_path: Base path for configuration files
        """
        self.base_path = base_path or os.getcwd()
        self.is_running = False
        self._start_time = None
        
    async def start(self):
        """Start file service."""
        try:
            # Create base path if it doesn't exist
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path)
                logger.info(f"Created config directory: {self.base_path}")
            
            self.is_running = True
            self._start_time = datetime.now()
            logger.info("File service started")
            
        except Exception as e:
            logger.error(f"Failed to start file service: {e}")
            raise create_error(
                status_code=503,
                message=f"Failed to start file service: {str(e)}"
            )
    
    async def stop(self):
        """Stop file service."""
        self.is_running = False
        self._start_time = None
        logger.info("File service stopped")
    
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
    
    def read(self, filename: str) -> str:
        """Read configuration file.
        
        Args:
            filename: Name of file to read
            
        Returns:
            str: File contents
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
        try:
            # Check if base path exists and is writable
            path_exists = os.path.exists(self.base_path)
            path_writable = os.access(self.base_path, os.W_OK)
            
            return {
                "status": "ok" if self.is_running else "error",
                "is_running": self.is_running,
                "uptime": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                "details": {
                    "base_path": self.base_path,
                    "path_exists": path_exists,
                    "path_writable": path_writable,
                    "config_count": len(self.list_configs()) if self.is_running else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "is_running": False,
                "uptime": 0,
                "details": {
                    "error": str(e)
                }
            }
