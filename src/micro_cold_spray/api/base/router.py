"""Base router functionality."""

import os
import psutil
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from loguru import logger

from .service import BaseService
from .errors import ErrorCode, format_error
from .exceptions import ServiceError


def add_health_endpoints(router: APIRouter, service: BaseService):
    """Add health check endpoints to router."""
    
    @router.get("/health", tags=["health"])
    async def health_check() -> Dict[str, Any]:
        """Get service health status."""
        try:
            # Get service health info
            health_info = await service.check_health()
            
            # Add process info
            process = psutil.Process(os.getpid())
            health_info["process_info"] = {
                "pid": process.pid,
                "memory": process.memory_info().rss / 1024 / 1024,  # MB
                "cpu_percent": process.cpu_percent()
            }
            
            # Add memory usage for backward compatibility
            health_info["memory_usage"] = health_info["process_info"]["memory"]
            
            # Add service info if not present
            if "service_info" not in health_info:
                health_info["service_info"] = {
                    "name": service._service_name,
                    "version": service.version,
                    "uptime": str(service.uptime) if service.is_running else None,
                    "running": service.is_running
                }
            
            # Add uptime for backward compatibility
            if "uptime" not in health_info and service.uptime:
                health_info["uptime"] = str(service.uptime)
            
            # Copy message and error to service_info if present
            if "message" in health_info:
                health_info["service_info"]["message"] = health_info["message"]
            if "error" in health_info:
                health_info["service_info"]["error"] = health_info["error"]
            
            return health_info

        except HTTPException:
            raise
        except ServiceError as e:
            logger.error(f"Health check failed: {e}")
            error = ErrorCode.HEALTH_CHECK_ERROR
            raise HTTPException(
                status_code=500,  # Internal Server Error
                detail=format_error(error, str(e))
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            error = ErrorCode.HEALTH_CHECK_ERROR
            raise HTTPException(
                status_code=500,  # Internal Server Error
                detail=format_error(error, str(e))
            )

    @router.post("/control")
    async def control_service(action: str):
        """Control service operation."""
        try:
            valid_actions = ["start", "stop", "restart"]
            if action not in valid_actions:
                error = ErrorCode.INVALID_ACTION
                raise HTTPException(
                    status_code=error.get_status_code(),
                    detail=format_error(
                        error,
                        f"Invalid action: {action}",
                        {"valid_actions": valid_actions}
                    )
                )

            if action == "stop":
                await service.stop()
                return {"status": "stopped"}
            elif action == "start":
                await service.start()
                return {"status": "started"}
            elif action == "restart":
                await service.stop()
                await service.start()
                return {"status": "restarted"}
        except HTTPException:
            raise
        except ServiceError as e:
            logger.error(f"Failed to {action} service: {e}")
            error = ErrorCode.SERVICE_UNAVAILABLE
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, str(e))
            )
        except Exception as e:
            logger.error(f"Failed to {action} service: {e}")
            error = ErrorCode.INTERNAL_ERROR
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, str(e))
            )
