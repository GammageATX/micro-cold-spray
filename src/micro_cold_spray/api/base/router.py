"""Base router functionality."""

from datetime import datetime
import psutil
import os
from fastapi import APIRouter, HTTPException
from loguru import logger


def add_health_endpoints(router: APIRouter, service):
    """Add health and control endpoints to router."""
    
    @router.get("/health", tags=["health"])
    async def health_check():
        """Check service health."""
        try:
            process = psutil.Process(os.getpid())
            memory = process.memory_info().rss

            # Get uptime if service has started
            uptime = 0
            if service.start_time is not None:
                uptime = (datetime.now() - service.start_time).total_seconds()

            # Get service-specific health status if available
            service_status = "ok"
            health_info = {}
            if hasattr(service, "check_health"):
                health_info = await service.check_health()
                if isinstance(health_info, dict):
                    service_status = health_info.get("status", "ok")
                else:
                    service_status = "error"
                    health_info = {"error": "Invalid health check response"}

            # Determine overall status
            status = "ok"
            if not service.is_running:
                status = "stopped"
            elif service_status == "error":
                status = "error"
            elif service_status == "degraded":
                status = "degraded"

            return {
                "status": status,
                "uptime": uptime,
                "memory_usage": memory,
                "service_info": {
                    "name": service._service_name,
                    "version": getattr(service, "version", "1.0.0"),
                    "running": service.is_running,
                    "error": health_info.get("error"),
                    **(health_info if isinstance(health_info, dict) else {})
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/control")
    async def control_service(action: str):
        """Control service operation."""
        try:
            if action not in ["start", "stop", "restart"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action: {action}"
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
        except Exception as e:
            logger.error(f"Failed to {action} service: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to {action} service: {str(e)}"
            )
