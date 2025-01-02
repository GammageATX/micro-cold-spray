"""Pattern service implementation."""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import status
from loguru import logger
from pathlib import Path

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.models.process_models import (
    Pattern,
    StatusType,
    PatternType
)


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
        self._failed_patterns = {}
        
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
            
            # Load patterns from data directory
            await self._load_patterns()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_patterns(self) -> None:
        """Load patterns from files."""
        try:
            pattern_dir = Path("data/patterns")
            if not pattern_dir.exists():
                return
            
            for pattern_file in pattern_dir.glob("*.yaml"):
                try:
                    with open(pattern_file, "r") as f:
                        data = yaml.safe_load(f)
                        
                    if "pattern" not in data:
                        logger.error(f"Missing 'pattern' root key in {pattern_file}")
                        continue
                        
                    pattern_data = data["pattern"]
                    # Convert type string to enum before validation
                    if "type" in pattern_data:
                        pattern_data["type"] = PatternType(pattern_data["type"])
                    
                    pattern = Pattern(**pattern_data)
                    self._patterns[pattern.id] = pattern
                    logger.info(f"Loaded pattern: {pattern.id}")
                        
                except Exception as e:
                    logger.error(f"Failed to load pattern {pattern_file}: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")

    async def _attempt_recovery(self) -> None:
        """Attempt to recover by reloading failed patterns."""
        if self._failed_patterns:
            logger.info(f"Attempting to recover {len(self._failed_patterns)} failed patterns...")
            await self._load_patterns()

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
            # Attempt recovery if there are failed patterns
            if self._failed_patterns:
                await self._attempt_recovery()
            
            # Check component health
            components = {
                "patterns": ComponentHealth(
                    status="ok" if self._patterns else "error",
                    error=None if self._patterns else "No patterns loaded"
                )
            }
            
            # Add failed patterns component if any exist
            if self._failed_patterns:
                failed_list = ", ".join(self._failed_patterns.keys())
                components["failed_patterns"] = ComponentHealth(
                    status="error",
                    error=f"Failed to load patterns: {failed_list}"
                )
            
            # Overall status is error only if no patterns loaded
            overall_status = "error" if not self._patterns else "ok"
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

    async def list_patterns(self) -> List[Pattern]:
        """List available patterns."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )
        
        return list(self._patterns.values())

    async def get_pattern(self, pattern_id: str) -> Pattern:
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

    async def create_pattern(self, pattern: Pattern) -> Pattern:
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

    async def update_pattern(self, pattern: Pattern) -> Pattern:
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
