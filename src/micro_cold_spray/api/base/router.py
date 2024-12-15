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
            uptime = (datetime.now() - service.start_time).total_seconds()
            memory = process.memory_info().rss

            # Get service-specific health status if available
            service_status = "ok"
            health_info = {}
            if hasattr(service, "check_health"):
                health_info = await service.check_health()
                service_status = health_info.get("status", "ok")

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
                    **health_info
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "service_info": {
                    "name": service._service_name,
                    "running": False,
                    "error": str(e)
                }
            }

    @router.post("/control")
    async def control_service(action: str):
        """Control service operation."""
        try:
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
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action: {action}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to {action} service: {str(e)}"
            )
