"""Messaging API package."""

from fastapi import FastAPI
from .service import MessagingService
from .router import router, lifespan
from micro_cold_spray.api.base.exceptions import MessageError, ValidationError

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)
app.include_router(router)

__all__ = [
    # Core components
    "MessagingService",
    "router",
    "app",
    # Exceptions
    "MessageError",
    "ValidationError"
]
