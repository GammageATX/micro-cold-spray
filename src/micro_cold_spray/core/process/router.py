"""Process management router."""

from typing import Optional, List
from fastapi import APIRouter, Depends, status

from micro_cold_spray.core.process.services.process_service import ProcessService
from micro_cold_spray.core.process.models.process import ProcessState, ProcessRequest, ProcessResponse
from micro_cold_spray.core.errors.codes import AppErrorCode
from micro_cold_spray.core.errors.formatting import raise_http_error
from micro_cold_spray.core.base import create_service_dependency


# Create router with prefix
router = APIRouter(
    prefix="/process",
    tags=["process"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)

# Global service instance
_service: Optional[ProcessService] = None


def init_router(service: ProcessService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service


# Create dependency for ProcessService
get_process_service = create_service_dependency(ProcessService)


@router.get(
    "/processes",
    response_model=List[ProcessState],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not available"}
    }
)
async def list_processes(service: ProcessService = Depends(get_process_service)):
    """List all processes."""
    return await service.list_processes()


@router.get(
    "/processes/{process_id}",
    response_model=ProcessState,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Process not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not available"}
    }
)
async def get_process(process_id: str, service: ProcessService = Depends(get_process_service)):
    """Get process by ID."""
    return await service.get_process(process_id)


@router.post(
    "/processes",
    response_model=ProcessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not available"}
    }
)
async def create_process(request: ProcessRequest, service: ProcessService = Depends(get_process_service)):
    """Create new process."""
    return await service.create_process(request)


@router.put(
    "/processes/{process_id}",
    response_model=ProcessResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Process not found"},
        status.HTTP_409_CONFLICT: {"description": "Invalid state transition"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not available"}
    }
)
async def update_process(
    process_id: str,
    request: ProcessRequest,
    service: ProcessService = Depends(get_process_service)
):
    """Update process state."""
    if request.process_id != process_id:
        raise_http_error(
            AppErrorCode.VALIDATION_ERROR,
            "Process ID mismatch"
        )
    return await service.update_process(request)


@router.delete(
    "/processes/{process_id}",
    response_model=ProcessResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Process not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not available"}
    }
)
async def delete_process(process_id: str, service: ProcessService = Depends(get_process_service)):
    """Delete process."""
    return await service.delete_process(process_id)
