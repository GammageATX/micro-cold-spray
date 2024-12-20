"""Base application module."""

import logging
from typing import Type, Optional, Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_service import BaseService


class BaseApp(FastAPI):
    """Base application class."""

    def __init__(
        self,
        service_class: Type[BaseService],
        title: str,
        service_name: str,
        enable_metrics: bool = False,
        **kwargs: Any,
    ):
        """Initialize base application.
        
        Args:
            service_class: Service class to instantiate
            title: Application title
            service_name: Service name
            enable_metrics: Enable metrics endpoint
            **kwargs: Additional FastAPI arguments
        """
        super().__init__(title=title, **kwargs)

        # Create service instance
        self.state.service = service_class(service_name)
        self.router = BaseRouter()

        # Add middleware
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add exception handlers
        self.add_exception_handler(RequestValidationError, self._handle_validation_error)
        self.add_exception_handler(Exception, self._handle_error)

        # Add middleware for logging
        self.middleware("http")(self._log_request)

        # Add lifespan events
        self.router.lifespan_context = self._lifespan_context

    async def _lifespan_context(self, app: FastAPI):
        """Manage service lifecycle.
        
        Args:
            app: FastAPI application instance
            
        Raises:
            HTTPException: If service fails to start (503)
        """
        try:
            await app.state.service.start()
            yield
        except Exception as e:
            raise create_error(
                message=f"{app.state.service.name} service failed to start",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                context={"service": app.state.service.name},
                cause=e
            )
        finally:
            try:
                await app.state.service.stop()
            except Exception as e:
                logging.error(f"Error stopping service: {str(e)}")

    async def _log_request(self, request: Request, call_next):
        """Log request details.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Raises:
            HTTPException: If request handling fails (500)
        """
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            raise create_error(
                message=str(e),
                status_code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
                context={"path": request.url.path},
                cause=e
            )

    async def _handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors.
        
        Args:
            request: FastAPI request
            exc: Validation error
            
        Returns:
            JSON response with error details (422)
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()}
        )

    async def _handle_error(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle general errors.
        
        Args:
            request: FastAPI request
            exc: Exception
            
        Returns:
            JSON response with error details (500 or status from exception)
        """
        if isinstance(exc, Exception) and hasattr(exc, "detail"):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

        error = create_error(
            message=str(exc),
            status_code=getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            context={"path": request.url.path},
            cause=exc
        )
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail}
        )
