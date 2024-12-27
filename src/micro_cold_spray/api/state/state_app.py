"""State service application."""

import os
import yaml
from typing import Dict, Any
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.state.state_service import StateService, load_config


def create_state_service() -> FastAPI:
    """Create state service.
    
    Returns:
        FastAPI: Application instance
    """
    # Load config
    config = load_config()
    version = config.get("version", "1.0.0")
    
    app = FastAPI(
        title="State Service",
        description="Service for managing system state",
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize service
    state_service = StateService()
    app.state.service = state_service
    app.state.config = config
    
    # Create dependency
    async def get_service() -> StateService:
        """Get state service instance.
        
        Returns:
            StateService: State service instance
        """
        return app.state.service
    
    @app.get("/health", response_model=ServiceHealth)
    async def health(service: StateService = Depends(get_service)) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        return await service.health()
    
    @app.post("/start")
    async def start(service: StateService = Depends(get_service)):
        """Start service."""
        await service.start()
        return {"status": "started"}
    
    @app.post("/stop")
    async def stop(service: StateService = Depends(get_service)):
        """Stop service."""
        await service.stop()
        return {"status": "stopped"}
    
    @app.get("/state")
    async def get_state(service: StateService = Depends(get_service)):
        """Get current state."""
        return {
            "state": service.current_state,
            "timestamp": service.uptime
        }
    
    @app.get("/transitions")
    async def get_transitions(service: StateService = Depends(get_service)):
        """Get valid state transitions."""
        return await service.get_valid_transitions()
    
    @app.post("/transition/{new_state}")
    async def transition(
        new_state: str,
        service: StateService = Depends(get_service)
    ):
        """Transition to new state."""
        return await service.transition_to(new_state)
    
    @app.get("/history")
    async def get_history(
        limit: int = None,
        service: StateService = Depends(get_service)
    ):
        """Get state history."""
        return await service.get_history(limit)
    
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
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop service on shutdown."""
        try:
            logger.info("Stopping state service...")
            await app.state.service.stop()
            logger.info("State service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop state service: {e}")
            # Don't raise during shutdown
    
    return app
