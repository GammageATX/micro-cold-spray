"""Base router module."""

from typing import Dict, Any, Callable, Awaitable

from fastapi import APIRouter, status
from fastapi.routing import APIRoute

from .base_errors import create_http_error


class BaseRouter(APIRouter):
    """Base router with health check endpoint."""

    def __init__(self, **kwargs: Any):
        """Initialize base router."""
        super().__init__(**kwargs)
        self.services = []
        self.root = None

        # Add health check endpoint
        self.add_api_route("/health", self._health_check, methods=["GET"])

    async def _health_check(self) -> Dict[str, Any]:
        """Get health status of all services."""
        services = []
        is_healthy = True
        service_status = "running"

        for service in self.services:
            try:
                health = await service.health()
                services.append(health)
                if not health["is_healthy"]:
                    is_healthy = False
                    service_status = "error"
            except Exception as e:
                is_healthy = False
                service_status = "error"
                services.append({
                    "is_healthy": False,
                    "status": "error",
                    "context": {
                        "service": service.name,
                        "error": str(e)
                    }
                })

        return {
            "is_healthy": is_healthy,
            "status": service_status,
            "context": {
                "services": services
            }
        }

    def get(self, path: str, **kwargs):
        """Add GET route."""
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, methods=["GET"], **kwargs)
            return func
        return decorator

    def post(self, path: str, **kwargs):
        """Add POST route."""
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, methods=["POST"], **kwargs)
            return func
        return decorator

    def put(self, path: str, **kwargs):
        """Add PUT route."""
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, methods=["PUT"], **kwargs)
            return func
        return decorator

    def delete(self, path: str, **kwargs):
        """Add DELETE route."""
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, methods=["DELETE"], **kwargs)
            return func
        return decorator

    def patch(self, path: str, **kwargs):
        """Add PATCH route."""
        def decorator(func: Callable) -> Callable:
            self.add_api_route(path, func, methods=["PATCH"], **kwargs)
            return func
        return decorator
