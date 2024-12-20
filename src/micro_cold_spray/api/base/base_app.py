"""Base FastAPI application with service management."""

from contextlib import asynccontextmanager
from typing import Type, Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_errors import create_error


class BaseApp(FastAPI):
    """Base FastAPI application with service management."""

    def __init__(
        self,
        service_class: Type[BaseService],
        title: str,
        service_name: str,
        enable_cors: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize base application.
        
        Args:
            service_class: Service class to instantiate
            title: API title
            service_name: Service name
            enable_cors: Whether to enable CORS
            **kwargs: Additional FastAPI arguments
        """
        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan context manager for FastAPI app."""
            try:
                # Initialize service
                app.state.service = service_class()
                await app.state.service.start()
                if not app.state.service.is_running:
                    raise create_error(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        message=f"{service_name} service failed to start"
                    )
                logger.info(f"{service_name} service started successfully")

                yield

            finally:
                # Cleanup on shutdown
                logger.info(f"{service_name} service shutting down")
                if hasattr(app.state, "service") and app.state.service:
                    try:
                        await app.state.service.stop()
                        logger.info(f"{service_name} service stopped successfully")
                    except Exception as e:
                        logger.error(f"Error stopping {service_name} service: {e}")
                    finally:
                        app.state.service = None

        # Initialize FastAPI with lifespan
        super().__init__(title=title, lifespan=lifespan, **kwargs)

        # Store service info
        self.service_class = service_class
        self.service_name = service_name

        # Add CORS middleware if enabled
        if enable_cors:
            self.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=False,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add logging middleware
        self.middleware("http")(self._log_request)

        # Create and add base router
        router = BaseRouter()
        self.include_router(router)

    async def _log_request(self, request, call_next):
        """Log request middleware."""
        response = await call_next(request)
        logger.info(
            f"HTTP Request: {request.method} {request.url} "
            f"\"{response.status_code} {response.headers.get('status', '')}\""
        )
        return response
