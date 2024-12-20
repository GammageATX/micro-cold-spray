"""Base FastAPI application with service management."""

from contextlib import asynccontextmanager
from typing import Type, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_router import BaseRouter


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
        super().__init__(title=title, **kwargs)

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
