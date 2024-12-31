"""Process API endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, status, Depends, HTTPException
from loguru import logger
import json
from pathlib import Path
import yaml
import time
from datetime import datetime

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus, ActionStatus, ProcessPattern, ParameterSet,
    SequenceMetadata, SequenceStep, Sequence, SequenceResponse,
    SequenceListResponse, PatternResponse, PatternListResponse,
    ParameterSetResponse, ParameterSetListResponse, NozzleListResponse,
    PowderListResponse
)
from micro_cold_spray.api.process.endpoints.list_endpoints import (
    list_patterns, list_parameters, list_sequences,
    list_nozzles, list_powders
)
from micro_cold_spray.api.process.endpoints.generate_endpoints import (
    generate_sequence, generate_pattern, generate_powder,
    generate_nozzle, generate_parameter
)
from micro_cold_spray.api.process.endpoints.dependencies import get_service
from micro_cold_spray.api.process.endpoints.sequence_endpoints import router as sequence_router


def create_process_router(process_service: ProcessService) -> APIRouter:
    """Create process router with endpoints."""
    process_router = APIRouter()
    
    # List endpoints
    process_router.add_api_route(
        "/patterns/list",
        list_patterns,
        methods=["GET"],
        response_model=PatternListResponse
    )
    process_router.add_api_route(
        "/parameters/list",
        list_parameters,
        methods=["GET"],
        response_model=ParameterSetListResponse
    )
    process_router.add_api_route(
        "/sequences/list",
        list_sequences,
        methods=["GET"],
        response_model=SequenceListResponse
    )
    process_router.add_api_route(
        "/nozzles/list",
        list_nozzles,
        methods=["GET"],
        response_model=NozzleListResponse
    )
    process_router.add_api_route(
        "/powders/list",
        list_powders,
        methods=["GET"],
        response_model=PowderListResponse
    )
    
    # Generate endpoints
    process_router.add_api_route(
        "/sequences/generate",
        generate_sequence,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/patterns/generate",
        generate_pattern,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/powders/generate",
        generate_powder,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/nozzles/generate",
        generate_nozzle,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/parameters/generate",
        generate_parameter,
        methods=["POST"]
    )
    
    # Add sequence execution endpoints
    process_router.include_router(sequence_router)
    
    return process_router
