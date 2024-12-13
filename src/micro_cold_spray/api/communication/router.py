"""FastAPI router for hardware communication."""

from fastapi import APIRouter, HTTPException, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import psutil
from datetime import datetime
import os
from loguru import logger

from .service import CommunicationService
from ..base.exceptions import ServiceError, ValidationError
from ..base.router import add_health_endpoints

# Create FastAPI app
app = FastAPI(title="Communication API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/communication", tags=["communication"])
_service: Optional[CommunicationService] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global _service
    _service = CommunicationService()
    await _service.start()
    # Add health endpoint directly to app
    add_health_endpoints(app, _service)  # Mount to app instead of router


def init_router(service: CommunicationService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    add_health_endpoints(router, service)


def get_service() -> CommunicationService:
    """Get communication service instance."""
    if _service is None:
        raise RuntimeError("Communication service not initialized")
    return _service


@router.get("/health")
async def health_check(
    service: CommunicationService = Depends(get_service)
) -> Dict[str, Any]:
    """Check API health status."""
    try:
        # Get base service health info
        process = psutil.Process(os.getpid())
        uptime = (datetime.now() - service.start_time).total_seconds()
        memory = process.memory_info().rss

        # Get communication-specific health status
        comm_status = await service.check_health()

        return {
            "status": "ok" if service.is_running and comm_status.get("status") == "ok" else "error",
            "uptime": uptime,
            "memory_usage": memory,
            "service_info": {
                "name": service._service_name,
                "version": getattr(service, "version", "1.0.0"),
                "running": service.is_running
            },
            "communication": comm_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "service_info": {
                "name": service._service_name,
                "running": False
            }
        }


@router.get("/clients")
async def get_clients(
    service: CommunicationService = Depends(get_service)
) -> Dict[str, Any]:
    """Get status of all communication clients."""
    try:
        clients = await service.get_client_status()
        return {"clients": clients}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/clients/{client_id}/connect")
async def connect_client(
    client_id: str,
    service: CommunicationService = Depends(get_service)
) -> Dict[str, str]:
    """Connect to a specific client."""
    try:
        await service.connect_client(client_id)
        return {"status": "connected"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/clients/{client_id}/disconnect")
async def disconnect_client(
    client_id: str,
    service: CommunicationService = Depends(get_service)
) -> Dict[str, str]:
    """Disconnect from a specific client."""
    try:
        await service.disconnect_client(client_id)
        return {"status": "disconnected"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/tags/{tag_path}")
async def read_tag(
    tag_path: str,
    service: CommunicationService = Depends(get_service)
) -> Dict[str, Any]:
    """Read a tag value."""
    try:
        value = await service.read_tag(tag_path)
        return {"tag": tag_path, "value": value}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/tags/{tag_path}")
async def write_tag(
    tag_path: str,
    value: Any,
    service: CommunicationService = Depends(get_service)
) -> Dict[str, str]:
    """Write a tag value."""
    try:
        await service.write_tag(tag_path, value)
        return {"status": "written"}
    except (ServiceError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# Include router in app
app.include_router(router)
