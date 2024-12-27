"""Pattern service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.models.process_models import ProcessPattern


class PatternService:
    """Service for managing process patterns."""

    def __init__(self):
        """Initialize pattern service."""
        self._start_time = time.time()
        self._is_running = False
        self._version = "1.0.0"
        self._service_name = "pattern"
        self._patterns: Dict[str, ProcessPattern] = {}

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time

    async def initialize(self) -> None:
        """Initialize service.
        
        Raises:
            Exception: If initialization fails
        """
        try:
            logger.info("Initializing pattern service...")
            
            # Load config
            config_path = os.path.join("config", "process.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if "pattern" in config:
                        self._version = config["pattern"].get("version", self._version)
                        
                        # Load patterns from config
                        patterns = config["pattern"].get("patterns", {})
                        for pattern_id, pattern_data in patterns.items():
                            self._patterns[pattern_id] = ProcessPattern(
                                id=pattern_id,
                                name=pattern_data.get("name", ""),
                                description=pattern_data.get("description", ""),
                                parameters=pattern_data.get("parameters", {})
                            )
            
            logger.info("Pattern service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize pattern service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def start(self) -> None:
        """Start service.
        
        Raises:
            Exception: If start fails
        """
        try:
            logger.info("Starting pattern service...")
            self._is_running = True
            logger.info("Pattern service started")
            
        except Exception as e:
            error_msg = f"Failed to start pattern service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            Exception: If stop fails
        """
        try:
            logger.info("Stopping pattern service...")
            self._is_running = False
            logger.info("Pattern service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop pattern service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Service health status
        """
        try:
            status = "healthy"
            error = None
            
            if not self.is_running:
                status = "error"
                error = "Service not running"
                
            return ServiceHealth(
                status=status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=error,
                components={}
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={}
            )

    async def list_patterns(self) -> List[ProcessPattern]:
        """List available patterns.
        
        Returns:
            List[ProcessPattern]: List of patterns
            
        Raises:
            Exception: If listing fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            return list(self._patterns.values())
            
        except Exception as e:
            error_msg = "Failed to list patterns"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def get_pattern(self, pattern_id: str) -> ProcessPattern:
        """Get pattern by ID.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            ProcessPattern: Pattern
            
        Raises:
            Exception: If pattern not found or retrieval fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if pattern_id not in self._patterns:
                raise Exception(f"Pattern {pattern_id} not found")
                
            return self._patterns[pattern_id]
            
        except Exception as e:
            error_msg = f"Failed to get pattern {pattern_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def create_pattern(self, pattern: ProcessPattern) -> ProcessPattern:
        """Create new pattern.
        
        Args:
            pattern: Pattern to create
            
        Returns:
            ProcessPattern: Created pattern
            
        Raises:
            Exception: If creation fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if pattern.id in self._patterns:
                raise Exception(f"Pattern {pattern.id} already exists")
                
            self._patterns[pattern.id] = pattern
            logger.info(f"Created pattern {pattern.id}")
            
            return pattern
            
        except Exception as e:
            error_msg = f"Failed to create pattern {pattern.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def update_pattern(self, pattern: ProcessPattern) -> ProcessPattern:
        """Update existing pattern.
        
        Args:
            pattern: Pattern to update
            
        Returns:
            ProcessPattern: Updated pattern
            
        Raises:
            Exception: If update fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if pattern.id not in self._patterns:
                raise Exception(f"Pattern {pattern.id} not found")
                
            self._patterns[pattern.id] = pattern
            logger.info(f"Updated pattern {pattern.id}")
            
            return pattern
            
        except Exception as e:
            error_msg = f"Failed to update pattern {pattern.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)

    async def delete_pattern(self, pattern_id: str) -> None:
        """Delete pattern.
        
        Args:
            pattern_id: Pattern identifier
            
        Raises:
            Exception: If deletion fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if pattern_id not in self._patterns:
                raise Exception(f"Pattern {pattern_id} not found")
                
            del self._patterns[pattern_id]
            logger.info(f"Deleted pattern {pattern_id}")
            
        except Exception as e:
            error_msg = f"Failed to delete pattern {pattern_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise Exception(error_msg)
