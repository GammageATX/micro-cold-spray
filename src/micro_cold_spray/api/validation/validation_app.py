"""Validation service application."""

from fastapi import status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base import add_health_endpoints
from micro_cold_spray.api.config import get_config_service
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.validation.validation_router import router


class ValidationApp(BaseApp):
    """Validation service application."""

    def __init__(self, **kwargs):
        """Initialize validation application.
        
        Args:
            **kwargs: Additional FastAPI arguments
            
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            # Get shared config service instance
            config_service = get_config_service()
            if not config_service.is_running:
                config_service.start()
                if not config_service.is_running:
                    raise create_error(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        message="ConfigService failed to start"
                    )
                logger.info("ConfigService started successfully")
            
            # Create and start message broker
            message_broker = MessagingService(config_service=config_service)
            message_broker.start()
            if not message_broker.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="MessageBroker failed to start"
                )
            logger.info("MessageBroker started successfully")
            
            # Initialize validation service
            validation_service = ValidationService(
                config_service=config_service,
                message_broker=message_broker
            )

            super().__init__(
                service_class=ValidationService,
                title="Validation Service",
                service_name="validation",
                **kwargs
            )

            # Add GZip middleware
            self.add_middleware(GZipMiddleware, minimum_size=1000)

            # Add CORS middleware
            self.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            # Add health endpoints
            add_health_endpoints(self, validation_service)

            # Include router
            self.include_router(router)
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize validation application",
                context={"error": str(e)},
                cause=e
            )


# Create FastAPI application instance
app = ValidationApp()
