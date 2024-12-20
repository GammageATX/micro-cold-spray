"""Base router module."""

from typing import List, Dict, Any, Optional, Callable
from fastapi import APIRouter, status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_service import BaseService


class BaseRouter(APIRouter):
    """Base router class."""

    def __init__(self):
        """Initialize base router."""
        super().__init__()
        self.services: List[BaseService] = []
        
        # Add health check endpoint
        self.add_api_route(
            "/health",
            self.check_health,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary="Get service health status",
            description="Returns the health status of all registered services"
        )

    def get(self, path: str, **kwargs: Any) -> Callable:
        """GET method decorator."""
        return super().get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable:
        """POST method decorator."""
        return super().post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable:
        """PUT method decorator."""
        return super().put(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable:
        """DELETE method decorator."""
        return super().delete(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable:
        """PATCH method decorator."""
        return super().patch(path, **kwargs)

    async def check_health(self) -> Dict[str, Any]:
        """Check health of all services.
        
        Returns:
            Health status of all services
        """
        services_health = []
        all_healthy = True

        for service in self.services:
            try:
                health = await service.health()
                services_health.append(health)
                if not health["is_healthy"]:
                    all_healthy = False
            except Exception as e:
                error_health = {
                    "is_healthy": False,
                    "status": "error",
                    "context": {
                        "service": service.name,
                        "error": str(e)
                    }
                }
                services_health.append(error_health)
                all_healthy = False

        return {
            "is_healthy": all_healthy,
            "status": "running" if all_healthy else "error",
            "context": {
                "services": services_health
            }
        }
