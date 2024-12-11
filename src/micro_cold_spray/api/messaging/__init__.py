"""Messaging API package."""

from .service import MessagingService
from .exceptions import MessagingError
from .router import router, init_router

__all__ = [
    # Core components
    "MessagingService",
    "router",
    "init_router",
    # Exceptions
    "MessagingError"
]
