"""Tag management endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from ..models.tags import TagSubscription, TagUpdate, TagMappingUpdateRequest
from ..service import CommunicationService
from ...base import get_service
from ...base.exceptions import ServiceError, ValidationError
from ...base.errors import ErrorCode, format_error

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/values")
async def get_tag_values(
    tags: str,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag values."""
    try:
        tag_list = [tag.strip() for tag in tags.split(",")]
        values = await service.tag_cache.get_values(tag_list)
        return {"values": values}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.post("/write")
async def write_tag_value(
    request: TagUpdate,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Write tag value."""
    try:
        await service.tag_cache.write_value(request.tag, request.value)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.post("/subscribe")
async def subscribe_to_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Subscribe to tag updates."""
    try:
        await service.tag_cache.subscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.post("/unsubscribe")
async def unsubscribe_from_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Unsubscribe from tag updates."""
    try:
        await service.tag_cache.unsubscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.get("/mappings")
async def get_tag_mappings(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag mappings."""
    try:
        mappings = await service.tag_mapping.get_mappings()
        return {"mappings": mappings}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.post("/mappings")
async def update_tag_mapping(
    request: TagMappingUpdateRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Update tag mapping."""
    try:
        await service.tag_mapping.update_mapping(request.tag_path, request.plc_tag)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )
