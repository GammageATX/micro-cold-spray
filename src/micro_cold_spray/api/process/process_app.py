# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

import os
import yaml
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints import router


DEFAULT_CONFIG = {
    "version": "1.0.0",
    "mode": "normal",
    "components": {
        "parameter": {"version": "1.0.0"},
        "pattern": {"version": "1.0.0"},
        "action": {"version": "1.0.0"},
        "sequence": {"version": "1.0.0"}
    }
}


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        config_path = os.path.join("config", "process.yaml")
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found: {config_path}")
            return DEFAULT_CONFIG
            
        with open(config_path) as f:
            return yaml.safe_load(f)
            
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to load configuration: {str(e)}"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle."""
    try:
        await app.state.service.initialize()
        await app.state.service.start()
        yield
    finally:
        if app.state.service.is_running:
            await app.state.service.stop()


def create_process_service() -> FastAPI:
    """Create process service application."""
    # Load config
    config = load_config()
    
    # Create service
    service = ProcessService(config)
    
    # Create FastAPI app
    app = FastAPI(
        title="Process API",
        description="Process control and execution API",
        version=config.get("version", "1.0.0"),
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store service in app state
    app.state.service = service
    
    # Mount router
    app.include_router(router, prefix="/process")
    
    return app
