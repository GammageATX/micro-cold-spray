"""Messaging service application."""

from fastapi import FastAPI, status
from fastapi.middleware.gzip import GZipMiddleware

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging.messaging_service import MessagingService
from micro_cold_spray.api.messaging.messaging_router import router


class MessagingApp(BaseApp):
    """Messaging service application."""

    def __init__(self, **kwargs):
        """Initialize messaging application.
        
        Args:
            **kwargs: Additional FastAPI arguments
            
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            super().__init__(
                service_class=MessagingService,
                title="Messaging Service",
                service_name="messaging",
                **kwargs
            )

            # Add GZip middleware
            self.add_middleware(GZipMiddleware, minimum_size=1000)

            # Include router
            self.include_router(router)
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize messaging application",
                context={"error": str(e)},
                cause=e
            )


# Create FastAPI application instance
app = MessagingApp()


# For backwards compatibility
def create_app(**kwargs) -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI: Application instance
        
    Raises:
        HTTPException: If app creation fails (503)
    """
    try:
        return MessagingApp(**kwargs)
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to create messaging application",
            context={"error": str(e)},
            cause=e
        )
