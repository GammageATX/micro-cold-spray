"""Validation service application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.validation.validation_router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.
    
    Args:
        app: FastAPI application
        
    Yields:
        None
    """
    try:
        # Initialize services
        config_service = ConfigService()
        message_broker = MessagingService()
        validation_service = ValidationService()
        
        # Store service references
        app.state.config_service = config_service
        app.state.message_broker = message_broker
        app.state.validation_service = validation_service
        
        # Initialize services
        await config_service.initialize()
        await message_broker.initialize()
        await validation_service.initialize(config_service, message_broker)
        
        logger.info("Validation service initialized")
        yield
        
        # Cleanup on shutdown
        await validation_service.stop()
        await message_broker.stop()
        await config_service.stop()
        logger.info("Validation service stopped")
        
    except Exception as e:
        logger.error(f"Service lifecycle error: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Service lifecycle error: {str(e)}"
        )


def create_app() -> FastAPI:
    """Create validation service application.
    
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Validation Service",
        description="Service for validating process data and configurations",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Add routes
    app.include_router(router)
    
    return app
