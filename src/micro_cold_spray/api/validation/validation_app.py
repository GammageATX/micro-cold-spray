"""Validation service application."""

import os
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.validation.validation_router import router


# Create FastAPI app
app = FastAPI(title="Validation Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize services
message_broker = None
validation_service = None


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    try:
        global message_broker, validation_service
        
        # Create services
        message_broker = MessagingService()
        validation_service = ValidationService()
        
        # Initialize services
        await message_broker.initialize()
        await validation_service.initialize(message_broker)
        
        logger.info("Validation service initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize validation service: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Failed to initialize validation service: {str(e)}"
        )


@app.on_event("shutdown")
async def shutdown():
    """Shutdown services."""
    try:
        global message_broker
        if message_broker:
            await message_broker.stop()
        logger.info("Validation service stopped")
    except Exception as e:
        logger.error(f"Error stopping validation service: {e}")


# Add validation endpoints
app.include_router(
    router,
    prefix="/api/validation",
    tags=["validation"]
)
