"""Communication router."""

from typing import Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from loguru import logger

from .service import CommunicationService
from ..base.router import create_api_app, get_service_from_app
from ..base.errors import ErrorCode, format_error
from ..base.exceptions import ServiceError
from .endpoints import equipment_router, motion_router, tags_router

# Create router without prefix (app already handles the /communication prefix)
router = APIRouter(tags=["communication"])

# Create FastAPI app with standard configuration
app = create_api_app(
    service_factory=CommunicationService,
    prefix="/communication",
    router=router,
    additional_routers=[equipment_router, motion_router, tags_router],
    config_type="hardware"  # Load hardware configuration
)


def init_router(service: CommunicationService) -> None:
    """Initialize router with service instance."""
    app.state.service = service


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
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(
                    error,
                    f"Invalid action: {action}",
                    {"valid_actions": valid_actions}
                )["detail"]
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
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )
