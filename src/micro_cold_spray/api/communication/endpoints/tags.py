from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Set

from ..models.tags import (
    TagRequest, TagResponse, TagWriteRequest, 
    TagCacheRequest, TagCacheResponse
)
from ..services.plc_service import PLCTagService
from ..services.feeder_service import FeederTagService
from ..services.tag_mapping import TagMappingService
from ..services.tag_cache import TagCacheService, ValidationError


# Dependency injection
async def get_config_manager():
    config_manager = ConfigManager()
    await config_manager.initialize()
    return config_manager


async def get_plc_service(
    config_manager: ConfigManager = Depends(get_config_manager)
) -> PLCTagService:
    service = PLCTagService(config_manager)
    await service.initialize()
    return service


async def get_feeder_service(
    config_manager: ConfigManager = Depends(get_config_manager)
) -> FeederTagService:
    service = FeederTagService(config_manager)
    await service.initialize()
    return service


async def get_tag_mapping_service(
    config_manager: ConfigManager = Depends(get_config_manager)
) -> TagMappingService:
    service = TagMappingService(config_manager)
    await service.initialize()
    return service


async def get_tag_cache_service(
    config_manager: ConfigManager = Depends(get_config_manager)
) -> TagCacheService:
    service = TagCacheService(config_manager)
    await service.initialize()
    return service


router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/read", response_model=TagResponse)
async def read_tag(
    request: TagRequest,
    tag_cache: TagCacheService = Depends(get_tag_cache_service)
):
    """
    Read a single tag value with metadata.

    This endpoint returns the current value of a tag along with its metadata
    (type, units, range, etc). All values are returned in engineering units
    (e.g., SLPM for flow, torr for pressure).

    Examples:
    ```python
    # Read a flow setpoint
    response = await client.post("/tags/read", json={
        "tag_path": "gas_control.main_flow.setpoint"
    })
    # Returns:
    {
        "tag": "gas_control.main_flow.setpoint",
        "value": 75.0,
        "metadata": {
            "type": "float",
            "access": "read/write",
            "description": "Main gas flow setpoint",
            "unit": "SLPM",
            "range": [0.0, 100.0]
        },
        "timestamp": "2024-01-10T12:34:56"
    }

    # Read a deagglomerator speed
    response = await client.post("/tags/read", json={
        "tag_path": "gas_control.hardware_sets.set1.deagglomerator.duty_cycle"
    })
    # Returns speed as human-readable string
    {
        "tag": "...",
        "value": "medium",
        "metadata": {
            "type": "string",
            "options": ["high", "medium", "low", "off"]
        }
    }
    ```
    """
    try:
        tag_value = tag_cache.get_tag_with_metadata(request.tag_path)
        return TagResponse(
            tag=request.tag_path,
            value=tag_value.value,
            metadata=tag_value.metadata,
            timestamp=tag_value.timestamp
        )
    except HardwareError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/write", response_model=TagResponse)
async def write_tag(
    request: TagWriteRequest,
    plc_service: PLCTagService = Depends(get_plc_service),
    feeder_service: FeederTagService = Depends(get_feeder_service),
    tag_mapping: TagMappingService = Depends(get_tag_mapping_service),
    tag_cache: TagCacheService = Depends(get_tag_cache_service)
):
    """
    Write a value to a tag.

    Values should be provided in engineering units or human-readable form.
    The API handles all necessary conversions (scaling, mapping, etc).

    Examples:
    ```python
    # Write a flow setpoint (in SLPM)
    await client.post("/tags/write", json={
        "tag_path": "gas_control.main_flow.setpoint",
        "value": 75.0
    })

    # Set deagglomerator speed
    await client.post("/tags/write", json={
        "tag_path": "gas_control.hardware_sets.set1.deagglomerator.duty_cycle",
        "value": "medium"  # API handles conversion to duty cycle
    })

    # Control a valve
    await client.post("/tags/write", json={
        "tag_path": "valve_control.main_gas",
        "value": true
    })
    ```

    Raises:
    - 400: Invalid tag path or hardware error
    - 422: Validation error (type mismatch, out of range, etc)
    """
    try:
        # Validate value before writing
        tag_cache.validate_value(request.tag_path, request.value)
        
        # Route to appropriate service based on tag type
        if tag_mapping.is_feeder_tag(request.tag_path):
            await feeder_service.write_tag(request.tag_path, request.value)
        elif tag_mapping.is_plc_tag(request.tag_path):
            await plc_service.write_tag(request.tag_path, request.value)
        else:
            raise HardwareError(f"Tag not mapped to hardware: {request.tag_path}", "mapping")
            
        # Get updated value with metadata
        tag_value = tag_cache.get_tag_with_metadata(request.tag_path)
        return TagResponse(
            tag=request.tag_path,
            value=tag_value.value,
            metadata=tag_value.metadata,
            timestamp=tag_value.timestamp
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HardwareError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cache", response_model=TagCacheResponse)
async def get_filtered_cache(
    filters: TagCacheRequest,
    tag_cache: TagCacheService = Depends(get_tag_cache_service)
):
    """
    Get filtered tag cache values.

    Returns all tag values that match the specified filters. If no filters
    are provided, returns all tags. All values are in engineering units
    or human-readable form.

    Examples:
    ```python
    # Get all gas control tags
    response = await client.post("/tags/cache", json={
        "groups": ["gas_control"]
    })

    # Get all writable numeric tags
    response = await client.post("/tags/cache", json={
        "types": ["float", "integer"],
        "access": ["read/write"]
    })

    # Get all motion status tags
    response = await client.post("/tags/cache", json={
        "groups": ["motion"],
        "types": ["bool"]
    })
    ```

    The response includes:
    - All matching tag values with metadata
    - List of groups present in the filtered results
    - Timestamp of the cache snapshot
    """
    try:
        all_tags = tag_cache.get_all_tags()
        filtered_tags = {}
        
        for tag_path, tag_value in all_tags.items():
            # Apply all filters
            if filters.groups and tag_value.metadata.group not in filters.groups:
                continue
                
            if filters.types and tag_value.metadata.type not in filters.types:
                continue
                
            if filters.access and tag_value.metadata.access not in filters.access:
                continue
                
            filtered_tags[tag_path] = tag_value
            
        # Get unique groups in response
        groups = {v.metadata.group for v in filtered_tags.values()}
            
        return TagCacheResponse(
            tags=filtered_tags,
            timestamp=datetime.now(),
            groups=groups
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups", response_model=Set[str])
async def get_tag_groups(
    tag_cache: TagCacheService = Depends(get_tag_cache_service)
):
    """
    Get available tag groups.

    Returns a list of all top-level tag groups available in the system.
    These groups can be used for filtering in the /cache endpoint.

    Example response:
    ```python
    [
        "gas_control",    # Gas flow and hardware settings
        "interlocks",     # Safety conditions
        "motion",         # Position, movement, status
        "pressure",       # Various pressure readings
        "relay_control",  # Hardware controls
        "safety",         # Safety parameters
        "status",        # System status
        "system_state",   # Overall state
        "vacuum_control", # Vacuum system
        "valve_control"   # Valve operations
    ]
    ```
    """
    try:
        all_tags = tag_cache.get_all_tags()
        return {v.metadata.group for v in all_tags.values()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))