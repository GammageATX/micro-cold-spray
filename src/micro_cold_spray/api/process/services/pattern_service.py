"""Pattern service implementation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.models.process_models import ProcessPattern


class PatternService:
    """Service for managing process patterns."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize pattern service."""
        self._service_name = "pattern"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._patterns = None
        
        logger.info(f"{self.service_name} service initialized")

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
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Initialize patterns
            self._patterns = {}
            
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
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            if self._patterns is None:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started")
            
        except Exception as e:
            self._is_running = False
            self._start_time = None
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )
            
            # 1. Clear pattern data
            self._patterns.clear()
            
            # 2. Reset service state
            self._is_running = False
            self._start_time = None
            
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Check component health
            components = {
                "patterns": ComponentHealth(
                    status="ok" if self._patterns else "error",
                    error=None if self._patterns else "No patterns loaded"
                )
            }
            
            # Overall status is error if any component is in error state
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            if not self.is_running:
                overall_status = "error"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
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
                components={"patterns": ComponentHealth(status="error", error=error_msg)}
            )

    async def list_patterns(self) -> List[ProcessPattern]:
        """List available patterns."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            return list(self._patterns.values())
            
        except Exception as e:
            error_msg = "Failed to list patterns"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_pattern(self, pattern_id: str) -> ProcessPattern:
        """Get pattern by ID."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if pattern_id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern_id} not found"
                )
                
            return self._patterns[pattern_id]
            
        except Exception as e:
            error_msg = f"Failed to get pattern {pattern_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def create_pattern(self, pattern: ProcessPattern) -> ProcessPattern:
        """Create new pattern."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if pattern.id in self._patterns:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Pattern {pattern.id} already exists"
                )
                
            self._patterns[pattern.id] = pattern
            logger.info(f"Created pattern {pattern.id}")
            
            return pattern
            
        except Exception as e:
            error_msg = f"Failed to create pattern {pattern.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def update_pattern(self, pattern: ProcessPattern) -> ProcessPattern:
        """Update existing pattern."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if pattern.id not in self._patterns:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern.id} not found"
                )
                
            self._patterns[pattern.id] = pattern
            logger.info(f"Updated pattern {pattern.id}")
            
            return pattern
            
        except Exception as e:
            error_msg = f"Failed to update pattern {pattern.id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
