"""Action service implementation."""

import os
import time
import yaml
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.process.models.process_models import ActionStatus


class ActionService:
    """Service for managing process actions."""

    def __init__(self, version: str = "1.0.0"):
        """Initialize action service."""
        self._service_name = "action"
        self._version = version
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._current_action = None
        self._action_status = ActionStatus.IDLE
        
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
            
            # Load config
            config_path = os.path.join("config", "process.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if "action" in config:
                        self._version = config["action"].get("version", self._version)
            
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
            
            # 1. Stop active actions
            if self._current_action:
                await self.stop_action(self._current_action)
            
            # 2. Clear action state
            self._current_action = None
            self._action_status = ActionStatus.IDLE
            
            # 3. Reset service state
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
            action_status = "ok"
            action_error = None
            
            if self._action_status == ActionStatus.ERROR:
                action_status = "error"
                action_error = "Action in error state"
            elif self._action_status == ActionStatus.RUNNING:
                action_status = "degraded"
                action_error = "Action in progress"
            
            components = {
                "action": ComponentHealth(
                    status=action_status,
                    error=action_error
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
                components={"action": ComponentHealth(status="error", error=error_msg)}
            )

    async def start_action(self, action_id: str) -> ActionStatus:
        """Start action execution."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if self._current_action:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Action {self._current_action} already in progress"
                )
                
            self._current_action = action_id
            self._action_status = ActionStatus.RUNNING
            logger.info(f"Started action {action_id}")
            
            return self._action_status
            
        except Exception as e:
            error_msg = f"Failed to start action {action_id}: {str(e)}"
            logger.error(error_msg)
            self._action_status = ActionStatus.ERROR
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop_action(self, action_id: str) -> ActionStatus:
        """Stop action execution."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if not self._current_action:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="No action in progress"
                )
                
            if action_id != self._current_action:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Action {action_id} not in progress"
                )
                
            self._current_action = None
            self._action_status = ActionStatus.IDLE
            logger.info(f"Stopped action {action_id}")
            
            return self._action_status
            
        except Exception as e:
            error_msg = f"Failed to stop action {action_id}: {str(e)}"
            logger.error(error_msg)
            self._action_status = ActionStatus.ERROR
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_action_status(self, action_id: str) -> ActionStatus:
        """Get action execution status."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )
                
            if not self._current_action:
                return ActionStatus.IDLE
                
            if action_id != self._current_action:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Action {action_id} not found"
                )
                
            return self._action_status
            
        except Exception as e:
            error_msg = f"Failed to get status for action {action_id}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
