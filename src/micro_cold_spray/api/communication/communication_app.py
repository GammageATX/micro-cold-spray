"""Communication service application."""

from fastapi import status
from fastapi.middleware.gzip import GZipMiddleware

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.communication_service import CommunicationService
from micro_cold_spray.api.communication.communication_router import router


class CommunicationApp(BaseApp):
    """Communication service application."""

    def __init__(self, **kwargs):
        """Initialize communication application.
        
        Args:
            **kwargs: Additional FastAPI arguments
            
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            super().__init__(
                service_class=CommunicationService,
                title="Communication Service",
                service_name="communication",
                **kwargs
            )

            # Add GZip middleware
            self.add_middleware(GZipMiddleware, minimum_size=1000)

            # Include router
            self.include_router(router)
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize communication application",
                context={"error": str(e)},
                cause=e
            )


# Create FastAPI application instance
app = CommunicationApp()
