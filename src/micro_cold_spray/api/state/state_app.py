"""State service application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

from micro_cold_spray.api.state.state_service import StateService
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


def create_state_service() -> FastAPI:
    """Create state service.
    
    Returns:
        FastAPI: Application instance
    """
    app = FastAPI(title="State Service")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )
    
    # Initialize service
    state_service = StateService()
    app.state.service = state_service
    
    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Get service health."""
        try:
            return HealthResponse(
                status="ok" if state_service.is_running else "error",
                service_name="state",
                version=getattr(state_service, "version", "1.0.0"),
                is_running=state_service.is_running,
                uptime=get_uptime(),
                memory_usage=get_memory_usage(),
                error=None if state_service.is_running else "Service not running",
                timestamp=datetime.now()
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return HealthResponse(
                status="error",
                service_name="state",
                version=getattr(state_service, "version", "1.0.0"),
                is_running=False,
                uptime=0.0,
                memory_usage={},
                error=error_msg,
                timestamp=datetime.now()
            )
    
    # Start service endpoint
    @app.post("/start")
    async def start():
        """Start service."""
        await state_service.start()
        return {"status": "started"}
    
    # Stop service endpoint
    @app.post("/stop")
    async def stop():
        """Stop service."""
        await state_service.stop()
        return {"status": "stopped"}
    
    # Get current state endpoint
    @app.get("/state")
    async def get_state():
        """Get current state."""
        return {
            "state": state_service.current_state,
            "timestamp": datetime.now().isoformat()
        }
    
    # Get valid transitions endpoint
    @app.get("/transitions")
    async def get_transitions():
        """Get valid state transitions."""
        return await state_service.get_valid_transitions()
    
    # Transition to new state endpoint
    @app.post("/transition/{new_state}")
    async def transition(new_state: str):
        """Transition to new state."""
        return await state_service.transition_to(new_state)
    
    # Get state history endpoint
    @app.get("/history")
    async def get_history(limit: int = None):
        """Get state history."""
        return await state_service.get_history(limit)
    
    # Add startup event to initialize service
    @app.on_event("startup")
    async def startup():
        """Start service on startup."""
        try:
            logger.info("Starting state service...")
            await state_service.start()
            logger.info("State service started successfully")
        except Exception as e:
            logger.error(f"Failed to start state service: {e}")
            raise
    
    # Add shutdown event to cleanup
    @app.on_event("shutdown")
    async def shutdown():
        """Stop service on shutdown."""
        try:
            logger.info("Stopping state service...")
            await state_service.stop()
            logger.info("State service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop state service: {e}")
            raise
    
    return app
