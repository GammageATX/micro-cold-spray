"""Action service implementation."""

import os
import time
import yaml
from typing import Dict, Any, Optional
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.models.process_models import ActionStatus


class ActionService:
    """Service for managing process actions."""

    def __init__(self):
        """Initialize action service."""
        self._start_time = time.time()
        self._is_running = False
        self._version = "1.0.0"
        self._service_name = "action"
        self._current_action = None
        self._action_status = ActionStatus.IDLE

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
            logger.info("Initializing action service...")
            
            # Load config
            config_path = os.path.join("config", "process.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if "action" in config:
                        self._version = config["action"].get("version", self._version)
            
            logger.info("Action service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize action service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def start(self) -> None:
        """Start service.
        
        Raises:
            Exception: If start fails
        """
        try:
            logger.info("Starting action service...")
            self._is_running = True
            logger.info("Action service started")
            
        except Exception as e:
            error_msg = f"Failed to start action service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            Exception: If stop fails
        """
        try:
            logger.info("Stopping action service...")
            
            # Stop current action if any
            if self._current_action:
                await self.stop_action(self._current_action)
            
            self._is_running = False
            logger.info("Action service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop action service: {str(e)}"
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
            elif self._action_status == ActionStatus.ERROR:
                status = "error"
                error = "Action in error state"
            elif self._action_status == ActionStatus.RUNNING:
                status = "degraded"
                error = "Action in progress"
                
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

    async def start_action(self, action_id: str) -> ActionStatus:
        """Start action execution.
        
        Args:
            action_id: Action identifier
            
        Returns:
            ActionStatus: Action execution status
            
        Raises:
            Exception: If start fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if self._current_action:
                raise Exception(f"Action {self._current_action} already in progress")
                
            self._current_action = action_id
            self._action_status = ActionStatus.RUNNING
            logger.info(f"Started action {action_id}")
            
            return self._action_status
            
        except Exception as e:
            error_msg = f"Failed to start action {action_id}: {str(e)}"
            logger.error(error_msg)
            self._action_status = ActionStatus.ERROR
            raise Exception(error_msg)

    async def stop_action(self, action_id: str) -> ActionStatus:
        """Stop action execution.
        
        Args:
            action_id: Action identifier
            
        Returns:
            ActionStatus: Action execution status
            
        Raises:
            Exception: If stop fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if not self._current_action:
                raise Exception("No action in progress")
                
            if action_id != self._current_action:
                raise Exception(f"Action {action_id} not in progress")
                
            self._current_action = None
            self._action_status = ActionStatus.IDLE
            logger.info(f"Stopped action {action_id}")
            
            return self._action_status
            
        except Exception as e:
            error_msg = f"Failed to stop action {action_id}: {str(e)}"
            logger.error(error_msg)
            self._action_status = ActionStatus.ERROR
            raise Exception(error_msg)

    async def get_action_status(self, action_id: str) -> ActionStatus:
        """Get action execution status.
        
        Args:
            action_id: Action identifier
            
        Returns:
            ActionStatus: Action execution status
            
        Raises:
            Exception: If status check fails
        """
        try:
            if not self.is_running:
                raise Exception("Service not running")
                
            if not self._current_action:
                return ActionStatus.IDLE
                
            if action_id != self._current_action:
                raise Exception(f"Action {action_id} not found")
                
            return self._action_status
            
        except Exception as e:
            error_msg = f"Failed to get status for action {action_id}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
