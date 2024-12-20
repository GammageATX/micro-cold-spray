"""Example service demonstrating simplified architecture."""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List

from micro_cold_spray.api.base.base_errors import create_error


class HealthResponse(BaseModel):
    """Health response model."""
    is_healthy: bool
    status: str
    details: Dict[str, Any]


def create_example_service() -> FastAPI:
    """Create example service.
    
    Returns:
        FastAPI: Application instance
    """
    app = FastAPI(title="Example Service")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )
    
    # Service state
    service_state = {
        "is_running": False,
        "error": None
    }
    
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Get service health."""
        return {
            "is_healthy": service_state["is_running"],
            "status": "running" if service_state["is_running"] else "stopped",
            "details": {
                "error": service_state["error"]
            }
        }
    
    @app.post("/start")
    async def start():
        """Start service."""
        if service_state["is_running"]:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message="Service already running"
            )
        
        try:
            # Implement service startup logic here
            service_state["is_running"] = True
            service_state["error"] = None
            return {"status": "started"}
        except Exception as e:
            service_state["error"] = str(e)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start service: {str(e)}",
                cause=e
            )
    
    @app.post("/stop")
    async def stop():
        """Stop service."""
        if not service_state["is_running"]:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message="Service not running"
            )
        
        try:
            # Implement service shutdown logic here
            service_state["is_running"] = False
            service_state["error"] = None
            return {"status": "stopped"}
        except Exception as e:
            service_state["error"] = str(e)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop service: {str(e)}",
                cause=e
            )
    
    return app
