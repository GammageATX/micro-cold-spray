"""Base router module."""

from typing import Dict, Any

from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel

from micro_cold_spray.api.base.base_errors import ServiceError, AppErrorCode
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_registry import get_service


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service_info: Dict[str, Any]


class BaseRouter(APIRouter):
    """Base router with health endpoint."""

    def __init__(self, service_class: type[BaseService], **kwargs: Any) -> None:
        """Initialize base router.
        
        Args:
            service_class: Service class to check health for
            **kwargs: Additional router arguments
        """
        super().__init__(**kwargs)
        self.service_class = service_class

        # Add health endpoint
        self.add_api_route(
            "/health",
            self._health_check,
            methods=["GET"],
            response_model=HealthResponse,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {
                    "description": "Service unavailable",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Service not available",
                                "code": AppErrorCode.SERVICE_UNAVAILABLE
                            }
                        }
                    }
                }
            }
        )

    async def _health_check(self) -> HealthResponse:
        """Check service health.
        
        Returns:
            Health check response
            
        Raises:
            HTTPException: If service is not available or other errors occur
        """
        try:
            service_factory = get_service(self.service_class)
            service = service_factory()
            health_info = await service.check_health()
            try:
                return HealthResponse(**health_info)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "detail": f"Invalid health response format: {e}",
                        "code": AppErrorCode.INTERNAL_ERROR
                    }
                )
        except ServiceError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={
                    "detail": str(e),
                    "code": e.error_code
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "detail": f"Unexpected error during health check: {e}",
                    "code": AppErrorCode.INTERNAL_ERROR
                }
            )
