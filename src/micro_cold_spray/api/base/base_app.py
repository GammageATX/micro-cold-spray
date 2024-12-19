from contextlib import asynccontextmanager
from typing import Type, Optional, Dict, Any, AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette import status

from micro_cold_spray.api.base.base_errors import ServiceError, AppErrorCode
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_registry import register_service, get_service, clear_services


class BaseApp(FastAPI):
    """Base FastAPI application with service management."""

    def __init__(
        self,
        service_class: Type[BaseService],
        title: str,
        service_name: str,
        enable_cors: bool = True,
        enable_metrics: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize base application.
        
        Args:
            service_class: Service class to instantiate
            title: API title
            service_name: Service name
            enable_cors: Whether to enable CORS
            enable_metrics: Whether to enable metrics endpoint
            **kwargs: Additional FastAPI arguments
        """
        # Create lifespan context before initializing FastAPI
        lifespan = self._create_lifespan()
        kwargs["lifespan"] = lifespan

        super().__init__(title=title, **kwargs)

        self.service_class = service_class
        self.service_name = service_name
        self.enable_metrics = enable_metrics

        # Add middleware
        if enable_cors:
            self.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add exception handlers
        self.add_exception_handler(ServiceError, self._handle_service_error)
        self.add_exception_handler(Exception, self._handle_unexpected_error)

        # Add middleware for logging
        self.middleware("http")(self._log_request)

        # Add health endpoint
        self.add_api_route("/health", self._health_check, methods=["GET"])

        # Add metrics endpoint
        if enable_metrics:
            self.add_api_route("/metrics", self._metrics, methods=["GET"])

    def _create_lifespan(self):
        """Create lifespan context manager."""
        @asynccontextmanager
        async def lifespan(app: FastAPI, receive=None, send=None):
            # Create and register service
            service = self.service_class(self.service_name)
            register_service(service)

            # Start service
            try:
                await service.start()
                yield
            finally:
                if service.is_running:
                    await service.stop()
                clear_services()

        return lifespan

    async def _health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        try:
            service = get_service(self.service_class)()
            health_info = await service.check_health()
            return health_info
        except ServiceError as e:
            raise ServiceError(
                str(e),
                error_code=e.error_code or AppErrorCode.SERVICE_UNAVAILABLE,
                status_code=e.status_code or status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e
        except Exception as e:
            raise ServiceError(
                f"Unexpected error during health check: {e}",
                error_code=AppErrorCode.INTERNAL_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from e

    async def _metrics(self) -> Dict[str, Any]:
        """Metrics endpoint."""
        try:
            service_factory = get_service(self.service_class)
            service = service_factory()
            return service.metrics
        except ServiceError as e:
            raise ServiceError(
                str(e),
                error_code=AppErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from e
        except Exception as e:
            raise ServiceError(
                f"Unexpected error getting metrics: {e}",
                error_code=AppErrorCode.INTERNAL_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from e

    async def _log_request(self, request: Request, call_next) -> Response:
        """Log request middleware."""
        response = await call_next(request)
        logger.info(
            f"HTTP Request: {request.method} {request.url} "
            f"\"{response.status_code} {response.headers.get('status', '')}\""
        )
        return response

    async def _handle_service_error(
        self,
        request: Request,
        exc: ServiceError,
    ) -> JSONResponse:
        """Handle service errors."""
        return JSONResponse(
            status_code=exc.status_code or status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc), "code": exc.error_code},
        )

    async def _handle_unexpected_error(
        self,
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected errors."""
        logger.exception("Unexpected error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "code": AppErrorCode.INTERNAL_ERROR,
            },
        )
