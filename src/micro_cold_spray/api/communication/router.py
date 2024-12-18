"""Communication router."""

from typing import Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from loguru import logger

from .service import CommunicationService
from ..base.router import create_api_app, get_service_from_app, add_health_endpoints
from ..base.errors import ErrorCode
from ..base.exceptions import ServiceError
from .endpoints import equipment_router, motion_router, tags_router

# Create router with prefix (app will handle the base /api/v1 prefix)
router = APIRouter(prefix="/communication", tags=["communication"])

# Create FastAPI app with standard configuration
app = create_api_app(
    service_factory=CommunicationService,
    prefix="/api/v1",
    router=router,
    additional_routers=[equipment_router, motion_router, tags_router],
    config_type="hardware"  # Load hardware configuration
)


def init_router(service: CommunicationService) -> None:
    """Initialize router with service instance."""
    app.state.service = service
    # Add health check endpoints
    add_health_endpoints(router, service)


def get_communication_service() -> CommunicationService:
    """Get communication service instance."""
    return get_service_from_app(app, CommunicationService)


@router.post("/control")
async def control_service(
    action: str,
    background_tasks: BackgroundTasks,
    service: CommunicationService = Depends(get_communication_service)
) -> Dict[str, str]:
    """Control service operation."""
    try:
        valid_actions = ["start", "stop", "restart"]
        if action not in valid_actions:
            error = ErrorCode.INVALID_ACTION
            error_detail = {
                "error": error.value,
                "message": f"Invalid action: {action}",
                "valid_actions": valid_actions
            }
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=error_detail
            )

        if action == "stop":
            await service.stop()
            background_tasks.add_task(logger.info, "Communication service stopped")
            return {"status": "stopped"}
        elif action == "start":
            await service.start()
            background_tasks.add_task(logger.info, "Communication service started")
            return {"status": "started"}
        elif action == "restart":
            await service.stop()
            await service.start()
            background_tasks.add_task(logger.info, "Communication service restarted")
            return {"status": "restarted"}
    except ServiceError as e:
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.COMMUNICATION_ERROR
        error_detail = {
            "error": error.value,
            "message": str(e)
        }
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=error_detail
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.INTERNAL_ERROR
        error_detail = {
            "error": error.value,
            "message": str(e)
        }
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=error_detail
        )
