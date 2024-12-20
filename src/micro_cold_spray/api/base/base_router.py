"""Base router module."""

from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import (
    create_error,
    SERVICE_ERROR
)


class HealthResponse(BaseModel):
    """Health check response model."""
    
    is_healthy: bool
    services: List[Dict[str, Any]]


class BaseRouter(APIRouter):
    """Base router with health check endpoint."""

    def __init__(self):
        """Initialize router with health check endpoint."""
        super().__init__()
        self.services: List[BaseService] = []
        
        @self.get("/health", response_model=HealthResponse)
        async def check_health() -> HealthResponse:
            """Check health of all services."""
            services_health = []
            for service in self.services:
                try:
                    health = await service.health()
                    services_health.append(health)
                except Exception as e:
                    error = create_error(
                        message=f"Health check failed for {service.name} service",
                        status_code=SERVICE_ERROR,
                        context={"service": service.name},
                        cause=e
                    )
                    services_health.append({
                        "is_healthy": False,
                        "status": "error",
                        "service": service.name,
                        "error": error.detail["message"]
                    })

            return HealthResponse(
                services=services_health,
                is_healthy=all(h["is_healthy"] for h in services_health)
            )
