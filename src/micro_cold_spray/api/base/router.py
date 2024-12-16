"""Base router functionality."""

import psutil
import os
from fastapi import APIRouter, HTTPException
from loguru import logger


def add_health_endpoints(router: APIRouter, service):
    """Add health check endpoints to router."""
    @router.get("/health", tags=["health"])
    async def health_check():
        """Get service health status."""
        try:
            # Get basic service info
            service_info = {
                "status": "ok" if service.is_running else "stopped",
                "uptime": service.uptime if service.is_running else None,
                "start_time": service.start_time.isoformat() if service.is_running and service.start_time else None,
                "process_info": {
                    "pid": os.getpid(),
                    "memory": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,  # MB
                    "cpu_percent": psutil.Process(os.getpid()).cpu_percent()
                }
            }

            # Get service-specific health info if available
            if service.is_running and hasattr(service, "check_health"):
                try:
                    health_info = await service.check_health()
                    if isinstance(health_info, dict):
                        service_info.update({
                            k: v for k, v in health_info.items()
                            if k not in service_info  # Avoid overwriting base info
                        })
                except Exception as e:
                    service_info["status"] = "error"
                    service_info["error"] = str(e)
            
            return service_info
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Health Check Failed", "message": str(e)}
            )

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
