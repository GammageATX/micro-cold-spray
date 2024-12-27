"""State service application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from datetime import datetime
from typing import Dict, Optional

from micro_cold_spray.api.state.state_service import StateService
from micro_cold_spray.utils.health import ServiceHealth, get_uptime


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
    @app.get("/health", response_model=ServiceHealth)
    async def health():
        """Get service health."""
        try:
            return ServiceHealth(
                status="ok" if state_service.is_running else "error",
                service="state",
                version=state_service.version,
                is_running=state_service.is_running,
                uptime=get_uptime(),
                error=None if state_service.is_running else "Service not running",
                components={
                    "state_machine": {
                        "status": "ok" if state_service.is_running else "error",
                        "error": None if state_service.is_running else "State machine not running"
                    }
                }
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="state",
                version=state_service.version,
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "state_machine": {
                        "status": "error",
                        "error": error_msg
                    }
                }
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
        """Start state service."""
        try:
            logger.info("Starting state service...")
            
            # Initialize service first
            await app.state.service.initialize()
            
            # Then start the service
            await app.state.service.start()
            
            logger.info("State service started successfully")
            
        except Exception as e:
            logger.error(f"State service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed
    
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
